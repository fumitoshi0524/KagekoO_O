"""Hooks engine — Claude Code-compatible lifecycle hooks for Kageko.

Supports hook types:
- PreToolUse: fired before a tool executes
- PostToolUse: fired after a tool completes
- SkillGenerated: fired after skill generation
- SkillEvaluated: fired after skill evaluation
- SkillActivated: fired when a skill is activated for a session

Each hook handler can be one of:
- command: execute a shell command
- prompt: ask the LLM to evaluate
- agent: dispatch a subagent
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable
import subprocess


class HookEvent(StrEnum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SKILL_GENERATED = "SkillGenerated"
    SKILL_EVALUATED = "SkillEvaluated"
    SKILL_ACTIVATED = "SkillActivated"


class HookResult(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CONTINUE = "continue"


@dataclass(slots=True, frozen=True, kw_only=True)
class HookContext:
    """Context passed to hook handlers when fired."""
    event: HookEvent
    tool_name: str = ""
    tool_input: str = ""
    tool_output: str = ""
    skill_name: str = ""
    session_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class HookHandler:
    """A single hook handler definition."""
    event: HookEvent
    handler_type: str  # "command", "prompt", "agent"
    command: str = ""
    prompt: str = ""
    agent_name: str = ""
    timeout_seconds: float = 30.0

    def execute(self, context: HookContext) -> HookResult:
        if self.handler_type == "command":
            return self._execute_command(context)
        elif self.handler_type == "prompt":
            return self._execute_prompt(context)
        elif self.handler_type == "agent":
            return self._execute_agent(context)
        return HookResult.CONTINUE

    def _execute_command(self, context: HookContext) -> HookResult:
        import os
        env = os.environ.copy()
        env["KAGEKO_HOOK_EVENT"] = str(context.event)
        env["KAGEKO_TOOL_NAME"] = context.tool_name
        env["KAGEKO_TOOL_INPUT"] = context.tool_input
        env["KAGEKO_TOOL_OUTPUT"] = context.tool_output
        env["KAGEKO_SKILL_NAME"] = context.skill_name

        try:
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=env,
            )
            output = result.stdout.strip()
            if output.lower().startswith("deny"):
                return HookResult.DENY
            if output.lower().startswith("allow"):
                return HookResult.ALLOW
            return HookResult.CONTINUE
        except subprocess.TimeoutExpired:
            return HookResult.CONTINUE
        except Exception:
            return HookResult.CONTINUE

    def _execute_prompt(self, context: HookContext) -> HookResult:
        # Prompt-type hooks are evaluated by the LLM at dispatch time.
        # Store the prompt template for the caller to use.
        return HookResult.CONTINUE

    def _execute_agent(self, context: HookContext) -> HookResult:
        # Agent-type hooks dispatch a subagent.
        # Store the agent name for the caller to use.
        return HookResult.CONTINUE


@dataclass(slots=True, kw_only=True)
class HooksEngine:
    """Central hooks registry and dispatcher."""

    _handlers: dict[HookEvent, list[HookHandler]] = field(default_factory=dict)

    def register(self, handler: HookHandler) -> None:
        self._handlers.setdefault(handler.event, []).append(handler)

    def unregister(self, event: HookEvent, handler: HookHandler) -> None:
        handlers = self._handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    def dispatch(self, context: HookContext) -> HookResult:
        """Dispatch an event to all registered handlers. Returns DENY if any handler denies."""
        handlers = self._handlers.get(context.event, [])
        final_result = HookResult.CONTINUE
        for handler in handlers:
            result = handler.execute(context)
            if result == HookResult.DENY:
                return HookResult.DENY
            if result == HookResult.ALLOW:
                final_result = HookResult.ALLOW
        return final_result

    def has_handlers(self, event: HookEvent) -> bool:
        return bool(self._handlers.get(event))

    def clear(self) -> None:
        self._handlers.clear()

    @classmethod
    def from_config(cls, config: list[dict[str, Any]]) -> HooksEngine:
        """Create a HooksEngine from a list of hook config dicts."""
        engine = cls()
        for item in config:
            event_str = item.get("event", "")
            try:
                event = HookEvent(event_str)
            except ValueError:
                continue
            handler = HookHandler(
                event=event,
                handler_type=item.get("type", "command"),
                command=item.get("command", ""),
                prompt=item.get("prompt", ""),
                agent_name=item.get("agent", ""),
                timeout_seconds=float(item.get("timeout", 30)),
            )
            engine.register(handler)
        return engine


def create_default_hooks() -> HooksEngine:
    """Create a hooks engine with sensible defaults (no handlers)."""
    return HooksEngine()
