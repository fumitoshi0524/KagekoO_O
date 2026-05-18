"""``process`` tool -- manage background sessions from ``terminal(background=true)``.

Parity with ClawCode -- same ProcessTool, create_process_tool.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from ...core.permission import PermissionRequest
from .base import BaseTool, ToolCall, ToolContext, ToolInfo, ToolResponse
from .process_registry import process_registry


def _session_owned(session_id: str, owner_session_id: str) -> bool:
    s = process_registry.get(session_id)
    if s is None:
        return False
    if not s.task_id:
        return True
    return s.task_id == owner_session_id


class ProcessTool(BaseTool):
    """Hermes-shaped process registry actions (list/poll/log/wait/kill/write/submit)."""

    def __init__(self, permissions: Any = None) -> None:
        self._permissions = permissions

    def info(self) -> ToolInfo:
        return ToolInfo(
            name="process",
            category="system",
            domain="technology",
            description=(
                "Manage background processes started with terminal(background=true). "
                "Actions: 'list' (show all for this task), 'poll', 'log', 'wait', 'kill', "
                "'write' (raw stdin), 'submit' (stdin + newline). "
                "session_id is required except for 'list'. "
                "Sessions are scoped to the agent session_id (task_id)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "poll", "log", "wait", "kill", "write", "submit"],
                        "description": "Action to perform",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Background process id (proc_...). Required except for list.",
                    },
                    "data": {
                        "type": "string",
                        "description": "Text for write/submit",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Seconds for wait (clamped by TERMINAL_TIMEOUT)",
                        "minimum": 1,
                    },
                    "offset": {"type": "integer", "description": "Line offset for log"},
                    "limit": {"type": "integer", "description": "Max lines for log", "minimum": 1},
                    "task_id": {
                        "type": "string",
                        "description": "Ignored in kageko; processes are always scoped to the current agent session.",
                    },
                },
                "required": ["action"],
            },
            required=["action"],
        )

    @property
    def is_dangerous(self) -> bool:
        return True

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        params = call.input if isinstance(call.input, dict) else {}
        action = str(params.get("action", "")).strip()
        owner = str(context.session_id or "").strip()
        session_id = str(params.get("session_id", "")).strip() if params.get("session_id") is not None else ""

        if self._permissions:
            desc = f"process action={action}" + (f" session={session_id}" if session_id else "")
            req = PermissionRequest(
                tool_name="process",
                description=desc,
                path=context.working_directory,
                input=params,
                session_id=context.session_id,
            )
            resp = await self._permissions.request(req)
            if not resp.granted:
                return ToolResponse(content="Permission denied for process tool", is_error=True)

        def _blocked() -> ToolResponse:
            return ToolResponse(
                content=json.dumps(
                    {"status": "forbidden", "error": "session_id does not belong to this agent session"},
                    ensure_ascii=False,
                ),
                is_error=True,
            )

        if action == "list":

            def _list() -> str:
                if not owner:
                    return json.dumps({"processes": []}, ensure_ascii=False)
                return json.dumps({"processes": process_registry.list_sessions(task_id=owner)}, ensure_ascii=False)

            out = await asyncio.to_thread(_list)
            return ToolResponse(content=out)

        if not session_id:
            return ToolResponse(
                content=json.dumps({"error": f"session_id is required for {action}"}, ensure_ascii=False),
                is_error=True,
            )

        if action in ("poll", "log", "wait", "kill", "write", "submit") and not _session_owned(session_id, owner):
            return _blocked()

        if action == "poll":

            def _poll() -> str:
                return json.dumps(process_registry.poll(session_id), ensure_ascii=False)

            return ToolResponse(content=await asyncio.to_thread(_poll))

        if action == "log":

            def _log() -> str:
                return json.dumps(
                    process_registry.read_log(
                        session_id,
                        offset=int(params.get("offset", 0) or 0),
                        limit=int(params.get("limit", 200) or 200),
                    ),
                    ensure_ascii=False,
                )

            return ToolResponse(content=await asyncio.to_thread(_log))

        if action == "wait":
            to = params.get("timeout")
            try:
                to_int = int(to) if to is not None else None
            except (TypeError, ValueError):
                to_int = None

            def _wait() -> str:
                return json.dumps(process_registry.wait(session_id, timeout=to_int), ensure_ascii=False)

            return ToolResponse(content=await asyncio.to_thread(_wait))

        if action == "kill":

            def _kill() -> str:
                return json.dumps(process_registry.kill_process(session_id), ensure_ascii=False)

            return ToolResponse(content=await asyncio.to_thread(_kill))

        if action == "write":

            def _write() -> str:
                return json.dumps(
                    process_registry.write_stdin(session_id, str(params.get("data", ""))),
                    ensure_ascii=False,
                )

            return ToolResponse(content=await asyncio.to_thread(_write))

        if action == "submit":

            def _submit() -> str:
                return json.dumps(
                    process_registry.submit_stdin(session_id, str(params.get("data", ""))),
                    ensure_ascii=False,
                )

            return ToolResponse(content=await asyncio.to_thread(_submit))

        return ToolResponse(
            content=json.dumps(
                {"error": f"Unknown process action: {action}"},
                ensure_ascii=False,
            ),
            is_error=True,
        )


def create_process_tool(permissions: Any = None) -> ProcessTool:
    return ProcessTool(permissions=permissions)
