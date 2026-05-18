"""TodoWrite / TodoRead tools for persistent task tracking.

Parity with ClawCode -- same TodoWriteTool, TodoReadTool, UpdateProjectStateTool,
create_todo_write_tool, create_todo_read_tool, create_update_project_state_tool.

Compatible with the Claude Code TodoWrite schema so that the TUI HUD
(which already parses ``TodoWrite`` tool-use events) works out of the box.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolCall, ToolContext, ToolInfo, ToolResponse


_TODO_FILENAME = ".kageko/todos.json"


def _todos_path(working_directory: str) -> Path:
    return Path(working_directory) / _TODO_FILENAME


def _load_todos(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_todos(path: Path, todos: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(todos, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# TodoWrite
# ---------------------------------------------------------------------------


def create_todo_write_tool(permissions: Any = None) -> "TodoWriteTool":
    return TodoWriteTool(permissions=permissions)


class TodoWriteTool(BaseTool):
    """Create or update a structured todo list (persistent, cross-session)."""

    def __init__(self, permissions: Any = None) -> None:
        self._permissions = permissions

    def info(self) -> ToolInfo:
        return ToolInfo(
            name="TodoWrite",
            category="operations",
            domain="technology",
            description=(
                "Create or update a persistent task list stored in "
                ".kageko/todos.json. Use this to track multi-step tasks, "
                "mark progress, and maintain continuity across sessions."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "description": "Array of TODO items to create or update.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Unique identifier for the todo item.",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Description of the todo item.",
                                },
                                "status": {
                                    "type": "string",
                                    "enum": [
                                        "pending",
                                        "in_progress",
                                        "completed",
                                        "cancelled",
                                    ],
                                    "description": "Current status.",
                                },
                            },
                            "required": ["id", "content", "status"],
                        },
                    },
                    "merge": {
                        "type": "boolean",
                        "description": (
                            "If true, merge into existing todos by id. "
                            "If false, replace the entire list."
                        ),
                        "default": False,
                    },
                },
                "required": ["todos"],
            },
            required=["todos"],
        )

    @property
    def requires_permission(self) -> bool:
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        params = call.get_input_dict()
        incoming = params.get("todos")
        if not isinstance(incoming, list):
            return ToolResponse.error("'todos' must be a list of todo items.")

        merge = bool(params.get("merge", False))
        path = _todos_path(context.working_directory)

        if merge:
            existing = _load_todos(path)
            idx = {t["id"]: i for i, t in enumerate(existing) if "id" in t}
            for item in incoming:
                tid = item.get("id")
                if not tid:
                    continue
                if tid in idx:
                    existing[idx[tid]].update(
                        {k: v for k, v in item.items() if v is not None}
                    )
                else:
                    item.setdefault("created_at", int(time.time()))
                    existing.append(item)
                    idx[tid] = len(existing) - 1
            todos = existing
        else:
            todos = []
            for item in incoming:
                item.setdefault("created_at", int(time.time()))
                todos.append(item)

        _save_todos(path, todos)

        completed = sum(1 for t in todos if t.get("status") == "completed")
        total = len(todos)
        return ToolResponse.text(
            f"Saved {total} todo(s) to {_TODO_FILENAME} ({completed}/{total} completed)."
        )


# ---------------------------------------------------------------------------
# TodoRead
# ---------------------------------------------------------------------------


def create_todo_read_tool(permissions: Any = None) -> "TodoReadTool":
    return TodoReadTool(permissions=permissions)


class TodoReadTool(BaseTool):
    """Read the current todo list."""

    def __init__(self, permissions: Any = None) -> None:
        self._permissions = permissions

    def info(self) -> ToolInfo:
        return ToolInfo(
            name="TodoRead",
            category="operations",
            domain="technology",
            description="Read the persistent todo list from .kageko/todos.json.",
            parameters={
                "type": "object",
                "properties": {},
            },
            required=[],
        )

    @property
    def requires_permission(self) -> bool:
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        path = _todos_path(context.working_directory)
        todos = _load_todos(path)
        if not todos:
            return ToolResponse.text("No todos found.")
        lines = []
        for t in todos:
            status = t.get("status", "pending")
            marker = {"completed": "x", "in_progress": ">", "cancelled": "-"}.get(
                status, " "
            )
            lines.append(f"[{marker}] {t.get('id', '?')}: {t.get('content', '')}")
        return ToolResponse.text("\n".join(lines))


# ---------------------------------------------------------------------------
# UpdateProjectState
# ---------------------------------------------------------------------------

_PROJECT_STATE_PATH = ".kageko/PROJECT_STATE.md"


def create_update_project_state_tool(permissions: Any = None) -> "UpdateProjectStateTool":
    return UpdateProjectStateTool(permissions=permissions)


class UpdateProjectStateTool(BaseTool):
    """Write or replace the project-level state file (.kageko/PROJECT_STATE.md).

    This file is automatically injected into the system prompt at the start
    of every session so the agent can resume work with full context.
    """

    def __init__(self, permissions: Any = None) -> None:
        self._permissions = permissions

    def info(self) -> ToolInfo:
        return ToolInfo(
            name="UpdateProjectState",
            category="operations",
            domain="technology",
            description=(
                "Write or replace .kageko/PROJECT_STATE.md -- a persistent memo "
                "injected into the system prompt of every new session. Use it to "
                "record milestones, architecture decisions, known issues, and "
                "next steps so that future sessions start with full context."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Full markdown content for PROJECT_STATE.md.",
                    },
                },
                "required": ["content"],
            },
            required=["content"],
        )

    @property
    def requires_permission(self) -> bool:
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        params = call.get_input_dict()
        content = params.get("content", "")
        if not content.strip():
            return ToolResponse.error("content must not be empty.")
        state_path = Path(context.working_directory) / _PROJECT_STATE_PATH
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(content, encoding="utf-8")
        return ToolResponse.text(
            f"PROJECT_STATE.md updated ({len(content)} chars). "
            "It will be injected into the system prompt of future sessions."
        )
