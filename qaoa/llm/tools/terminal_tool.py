"""``terminal`` tool -- foreground execution or background spawn (local PTY/pipe or sandbox nohup).

Parity with ClawCode -- same TerminalTool, create_terminal_tool.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from ...config.settings import ShellConfig, get_settings
from ...core.permission import PermissionRequest
from ...utils.text import sanitize_text, strip_ansi_escapes
from .base import BaseTool, ToolCall, ToolContext, ToolInfo, ToolResponse
from .bash import (
    SAFE_COMMANDS,
    _coerce_bash_timeout,
    _create_shell_process_with_fallback,
    _decode_bytes,
    _effective_bash_cwd,
    _prepare_command,
    _resolve_environments_backend,
)
from .process_registry import process_registry

logger = logging.getLogger(__name__)


def _resolve_shell_config() -> ShellConfig:
    try:
        return get_settings().shell
    except Exception:
        return ShellConfig()


def _parse_check_interval(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        v = int(raw)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _apply_background_watcher(
    session: Any,
    *,
    check_interval: int | None,
    session_key: str,
) -> dict[str, Any]:
    """Set watcher fields and enqueue ``pending_watchers`` (Hermes-aligned)."""
    extra: dict[str, Any] = {}
    if getattr(session, "exited", False):
        return extra
    if not check_interval or check_interval <= 0:
        return extra
    effective = max(30, check_interval)
    if check_interval < 30:
        extra["check_interval_note"] = (
            f"Requested check_interval={check_interval}s raised to minimum 30s"
        )
    session.session_key = session_key or getattr(session, "session_key", "") or ""
    session.watcher_platform = os.getenv("KAGEKO_SESSION_PLATFORM", "").strip() or os.getenv(
        "HERMES_SESSION_PLATFORM", ""
    ).strip()
    session.watcher_chat_id = os.getenv("KAGEKO_SESSION_CHAT_ID", "").strip() or os.getenv(
        "HERMES_SESSION_CHAT_ID", ""
    ).strip()
    session.watcher_thread_id = os.getenv("KAGEKO_SESSION_THREAD_ID", "").strip() or os.getenv(
        "HERMES_SESSION_THREAD_ID", ""
    ).strip()
    session.watcher_interval = effective
    process_registry.enqueue_watcher_for_session(session)
    process_registry._write_checkpoint()
    return extra


def _terminal_requires_permission(command: str) -> bool:
    parts = command.strip().split()
    if not parts:
        return False
    cmd = parts[0]
    return not (
        cmd in SAFE_COMMANDS
        or (cmd == "git" and len(parts) > 1 and f"git {parts[1]}" in SAFE_COMMANDS)
    )


class TerminalTool(BaseTool):
    """Run a shell command in the configured terminal environment or spawn a background job."""

    def __init__(self, permissions: Any = None) -> None:
        self._permissions = permissions

    def info(self) -> ToolInfo:
        return ToolInfo(
            name="terminal",
            category="operations",
            domain="technology",
            description=(
                "Run a shell command with the same environment stack as bash (KAGEKO_TERMINAL_ENV / "
                "create_environment). Use foreground (default) for one-shot output. "
                "Set background=true to spawn a managed session (session_id in JSON); use the process tool "
                "to poll or send stdin. pty=true requests a PTY on POSIX when ptyprocess is installed; "
                "Windows uses pipe mode. Non-local backends use nohup + log polling (no interactive stdin)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."},
                    "workdir": {
                        "type": "string",
                        "description": "Working directory (alias: cwd). Defaults to session workspace.",
                    },
                    "cwd": {"type": "string", "description": "Alias of workdir."},
                    "background": {
                        "type": "boolean",
                        "description": "If true, spawn and return session_id without blocking.",
                        "default": False,
                    },
                    "pty": {
                        "type": "boolean",
                        "description": "If true, prefer PTY for background local sessions (POSIX).",
                        "default": False,
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (foreground; default 180).",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Optional; defaults to the current agent session id for scoping.",
                    },
                    "session_key": {
                        "type": "string",
                        "description": "Optional gateway/session key; defaults to agent session id.",
                    },
                    "check_interval": {
                        "type": "integer",
                        "description": (
                            "Background only: poll interval in seconds for TUI completion notifications "
                            "(minimum 30). Uses KAGEKO_SESSION_* env vars when set."
                        ),
                        "minimum": 1,
                    },
                },
                "required": ["command"],
            },
            required=["command"],
        )

    @property
    def is_dangerous(self) -> bool:
        return True

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        params = call.input if isinstance(call.input, dict) else {}
        raw_cmd = params.get("command", "")
        command_in = raw_cmd if isinstance(raw_cmd, str) else ""
        command_in = command_in.strip()
        if not command_in:
            return ToolResponse(content=json.dumps({"error": "No command provided"}, ensure_ascii=False), is_error=True)

        background = bool(params.get("background", False))
        use_pty = bool(params.get("pty", False))
        timeout = _coerce_bash_timeout(params.get("timeout", 180), default=180.0)

        merged_params = dict(params)
        if params.get("workdir") and not params.get("cwd"):
            merged_params["cwd"] = params.get("workdir")
        cwd = _effective_bash_cwd(merged_params, context)

        task_id = str(params.get("task_id") or context.session_id or "").strip()
        session_key = str(params.get("session_key") or context.session_id or "").strip()
        check_interval = _parse_check_interval(params.get("check_interval"))

        if _terminal_requires_permission(command_in) and self._permissions:
            req = PermissionRequest(
                tool_name="terminal",
                description=f"Terminal: {'background ' if background else ''}{command_in[:200]}",
                path=cwd,
                input=params,
                session_id=context.session_id,
            )
            resp = await self._permissions.request(req)
            if not resp.granted:
                return ToolResponse(content="Permission denied for terminal", is_error=True)

        use_backend, backend_type = _resolve_environments_backend()

        if background:
            return await self._run_background(
                command_in,
                cwd=cwd,
                task_id=task_id,
                session_key=session_key,
                check_interval=check_interval,
                use_backend=use_backend,
                backend_type=backend_type,
                use_pty=use_pty,
                timeout=int(max(1, round(timeout))),
            )

        return await self._run_foreground(
            command_in,
            cwd=cwd,
            use_backend=use_backend,
            backend_type=backend_type,
            timeout=int(max(1, round(timeout))),
        )

    async def _run_foreground(
        self,
        command_in: str,
        *,
        cwd: str | None,
        use_backend: bool,
        backend_type: str,
        timeout: int,
    ) -> ToolResponse:
        if use_backend:
            from .environments.factory import create_environment

            cwd_eff = (cwd or "").strip() or os.getcwd()
            env = create_environment(
                backend_type,
                cwd=cwd_eff,
                timeout=timeout,
                persistent=False,
            )
            try:
                result = await env.execute_async(
                    command_in,
                    cwd=cwd_eff or "",
                    timeout=timeout,
                )
            finally:
                env.cleanup()
            out = sanitize_text(strip_ansi_escapes(str(result.get("output", ""))))
            rc = int(result.get("returncode", -1))
            payload = json.dumps(
                {"output": out, "returncode": rc, "backend": backend_type},
                ensure_ascii=False,
            )
            if rc != 0:
                return ToolResponse(content=payload, is_error=True)
            return ToolResponse(content=payload)

        prep = _prepare_command(command_in)
        try:
            process, active_prep = await _create_shell_process_with_fallback(command_in, cwd, prep=prep)
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=float(timeout),
            )
            out = sanitize_text(strip_ansi_escapes(_decode_bytes(stdout)))
            err = sanitize_text(strip_ansi_escapes(_decode_bytes(stderr)))
            rc = process.returncode if process.returncode is not None else -1
            body = out
            if err:
                body = f"{out}\n{err}".strip() if out else err
            payload = json.dumps(
                {"output": body, "returncode": rc, "backend": "local"},
                ensure_ascii=False,
            )
            if rc != 0:
                return ToolResponse(content=payload, is_error=True)
            return ToolResponse(content=payload)
        except TimeoutError:
            return ToolResponse(
                content=json.dumps(
                    {"error": f"Command timed out after {timeout}s", "returncode": 124},
                    ensure_ascii=False,
                ),
                is_error=True,
            )
        except Exception as e:
            logger.exception("terminal foreground failed")
            return ToolResponse(
                content=json.dumps({"error": str(e)}, ensure_ascii=False),
                is_error=True,
            )

    async def _run_background(
        self,
        command_in: str,
        *,
        cwd: str | None,
        task_id: str,
        session_key: str,
        check_interval: int | None,
        use_backend: bool,
        backend_type: str,
        use_pty: bool,
        timeout: int,
    ) -> ToolResponse:
        if use_backend and backend_type != "local":
            from .environments.factory import create_environment

            cwd_eff = (cwd or "").strip() or os.getcwd()
            env = create_environment(
                backend_type,
                cwd=cwd_eff,
                timeout=timeout,
                persistent=False,
            )

            def _spawn() -> Any:
                return process_registry.spawn_via_env(
                    env,
                    command_in,
                    cwd=cwd_eff,
                    task_id=task_id,
                    session_key=session_key,
                    timeout=timeout,
                )

            session = await asyncio.to_thread(_spawn)
            wextra = _apply_background_watcher(
                session,
                check_interval=check_interval,
                session_key=session_key,
            )
            payload = {
                "status": "started",
                "session_id": session.id,
                "backend": backend_type,
                "note": (
                    "Non-local sandbox: output is log-polled; stdin write/submit are not available "
                    "for this backend."
                ),
            }
            payload.update(wextra)
            return ToolResponse(content=json.dumps(payload, ensure_ascii=False))

        cwd_eff = (cwd or "").strip() or os.getcwd()
        extra_env = None
        try:
            sh = _resolve_shell_config()
            if sh.env:
                extra_env = dict(sh.env)
        except Exception:
            extra_env = None

        def _spawn_local() -> Any:
            return process_registry.spawn_local(
                command_in,
                cwd=cwd_eff,
                task_id=task_id,
                session_key=session_key,
                env_vars=extra_env,
                use_pty=use_pty,
            )

        session = await asyncio.to_thread(_spawn_local)
        wextra = _apply_background_watcher(
            session,
            check_interval=check_interval,
            session_key=session_key,
        )
        body: dict[str, Any] = {
            "status": "started",
            "session_id": session.id,
            "backend": "local",
            "pid": session.pid,
        }
        body.update(wextra)
        return ToolResponse(content=json.dumps(body, ensure_ascii=False))


def create_terminal_tool(permissions: Any = None) -> TerminalTool:
    return TerminalTool(permissions=permissions)
