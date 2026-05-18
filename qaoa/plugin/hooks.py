from __future__ import annotations

import asyncio
import json
import locale
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .types import HookDecision, HookEvent, HookHandler, HookHandlerType, HookMatcherGroup, LoadedPlugin

logger = logging.getLogger(__name__)


_PLUGIN_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _substitute_plugin_vars(s: str, vars_map: dict[str, str]) -> str:
    """Substitute ${KAGEKO_PLUGIN_ROOT}/${KAGEKO_PLUGIN_DATA} placeholders."""

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        return vars_map.get(key, m.group(0))

    return _PLUGIN_VAR_PATTERN.sub(repl, s)


def _try_parse_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def _extract_permission_decision(raw_json: dict[str, Any] | None) -> HookDecision | None:
    if not raw_json:
        return None

    # Claude Code wraps decisions in hookSpecificOutput.
    out = raw_json.get("hookSpecificOutput") if isinstance(raw_json.get("hookSpecificOutput"), dict) else raw_json
    if not isinstance(out, dict):
        return None

    if "permissionDecision" not in out and "permissionDecisionReason" not in out:
        return None

    decision = HookDecision.model_validate(out)
    return decision


@dataclass(frozen=True)
class HookMatchContext:
    """Context for matcher evaluation."""

    # Claude Code matcher is regex; for tool events it matches on `tool_name`.
    tool_name: str | None = None

    # raw context we pass to hooks
    event: HookEvent | None = None
    session_id: str | None = None
    tool_input: dict[str, Any] | None = None
    additional: dict[str, Any] | None = None


class HookEngine:
    """A minimal Claude Code compatible hook execution engine.

    Phase 2 focuses on making PreToolUse/PostToolUse hooks executable so
    the system can block destructive tools and allow side-effect automation.
    """

    def __init__(self, plugins: list[LoadedPlugin]) -> None:
        self._plugins = plugins

    def _iter_hook_groups(
        self,
        event: HookEvent,
        match_value: str | None,
    ) -> list[tuple[LoadedPlugin, HookMatcherGroup]]:
        groups: list[tuple[LoadedPlugin, HookMatcherGroup]] = []

        # Claude Code compatibility:
        # - Only tool-related events use `matcher` (tool name regex).
        # - Other events ignore `matcher` and always fire.
        matcher_supported_events = {
            HookEvent.PreToolUse,
            HookEvent.PostToolUse,
            HookEvent.PostToolUseFailure,
            HookEvent.PermissionRequest,
        }
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            for group in plugin.hooks.get(event, []):
                matcher = (group.matcher or "").strip()

                if event not in matcher_supported_events:
                    groups.append((plugin, group))
                    continue

                if matcher in {"", "*"}:
                    groups.append((plugin, group))
                    continue
                if match_value is None:
                    continue
                try:
                    if re.search(matcher, match_value):
                        groups.append((plugin, group))
                except re.error:
                    # invalid regex: ignore
                    continue

        return groups

    # QAOA observation hook: record tool output
    async def fire(
        self,
        event: HookEvent,
        *,
        match_value: str | None = None,
        context: dict[str, Any] | None = None,
        provider: Any | None = None,
        working_directory: str | None = None,
        plugin_var_map: dict[str, str] | None = None,
        agent_tools: list[dict[str, Any]] | None = None,
        suppress_agent_hooks: bool = False,
    ) -> list[HookDecision]:
        """Fire a hook event and return collected decisions.

        Returns:
            A list of HookDecision objects extracted from hook outputs.
        """

        context = context or {}
        plugin_var_map = plugin_var_map or {}
        working_directory = working_directory or os.getcwd()

        decisions: list[HookDecision] = []
        groups = self._iter_hook_groups(event, match_value)
        if not groups:
            return decisions

        # Execute in registration order for determinism.
        for plugin, group in groups:
            for handler in group.hooks:
                if handler.type == HookHandlerType.AGENT and suppress_agent_hooks:
                    continue

                try:
                    dec = await self._execute_handler(
                        handler,
                        event=event,
                        context=context,
                        provider=provider,
                        working_directory=working_directory,
                        plugin_var_map=plugin_var_map,
                        agent_tools=agent_tools,
                    )
                    if dec:
                        decisions.append(dec)
                except Exception as e:
                    logger.warning("Hook execution failed: %s (%s)", e, handler)
                    continue

        return decisions

    async def _execute_handler(
        self,
        handler: HookHandler,
        *,
        event: HookEvent,
        context: dict[str, Any],
        provider: Any | None,
        working_directory: str,
        plugin_var_map: dict[str, str],
        agent_tools: list[dict[str, Any]] | None,
    ) -> HookDecision | None:
        if handler.type == HookHandlerType.COMMAND:
            command = handler.command or ""
            if not command:
                return None
            command = _substitute_plugin_vars(command, plugin_var_map)
            return await self._run_command_hook(
                command,
                context=context,
                working_directory=working_directory,
            )

        if handler.type == HookHandlerType.PROMPT:
            if provider is None:
                return None
            prompt_template = handler.prompt or ""
            if not prompt_template:
                return None

            payload = json.dumps(context, ensure_ascii=False)
            rendered = prompt_template.replace("$ARGUMENTS", payload)
            return await self._run_prompt_hook(
                provider=provider,
                rendered_prompt=rendered,
            )

        if handler.type == HookHandlerType.AGENT:
            # Minimal implementation: run a single LLM evaluation prompt.
            # Full agentic subagent support can be added later.
            if provider is None:
                return None
            agent_cfg = handler.agent or {}
            instructions = ""
            if isinstance(agent_cfg, dict):
                instructions = str(agent_cfg.get("instructions") or agent_cfg.get("prompt") or "")
            if not instructions:
                # Fallback: use event name
                instructions = f"Evaluate the hook for event {event} with context: $ARGUMENTS"
            payload = json.dumps(context, ensure_ascii=False)
            rendered = instructions.replace("$ARGUMENTS", payload)

            return await self._run_prompt_hook(
                provider=provider,
                rendered_prompt=rendered,
            )

        return None

    async def _run_command_hook(
        self,
        command: str,
        *,
        context: dict[str, Any],
        working_directory: str,
    ) -> HookDecision | None:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=working_directory,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert proc.stdin and proc.stdout and proc.stderr
        stdin_bytes = json.dumps(context, ensure_ascii=False).encode("utf-8", errors="replace")
        proc.stdin.write(stdin_bytes)
        await proc.stdin.drain()
        proc.stdin.close()

        stdout, stderr = await proc.communicate()
        if stderr:
            # Don't spam logs unless debug.
            logger.debug("Hook command stderr: %s", stderr.decode("utf-8", errors="replace"))

        # Decode stdout using system preferred encoding for better Windows behavior.
        decoded = stdout.decode(locale.getpreferredencoding(False) or "utf-8", errors="replace")
        raw = _try_parse_json(decoded.strip())
        return _extract_permission_decision(raw)

    async def _run_prompt_hook(
        self,
        *,
        provider: Any,
        rendered_prompt: str,
    ) -> HookDecision | None:
        # Hook prompt is expected to return JSON. If not, we ignore.
        resp = await provider.send_messages(
            [
                {"role": "user", "content": rendered_prompt},
            ],
            tools=None,
        )
        content = getattr(resp, "content", "") or ""
        raw = _try_parse_json(content.strip())
        return _extract_permission_decision(raw)
