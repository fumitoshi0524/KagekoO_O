# src/kageko/tools/builtin/system_tools.py
from __future__ import annotations

from typing import Any


# In-memory todo list for v1
_todos: list[dict[str, Any]] = []


async def echo(args: dict[str, Any]) -> str:
    return args.get("text", "")


async def todo_add(args: dict[str, Any]) -> str:
    task = args.get("task")
    if not task:
        return "[ERROR] Missing required parameter: 'task'"
    priority = args.get("priority", "medium")
    _todos.append({"task": task, "priority": priority, "done": False})
    return f"Added: [{priority}] {task}"


async def todo_list(args: dict[str, Any]) -> str:
    if not _todos:
        return "(no tasks)"
    lines = []
    for i, item in enumerate(_todos, 1):
        status = "[x]" if item["done"] else "[ ]"
        lines.append(f"{i}. {status} [{item['priority']}] {item['task']}")
    return "\n".join(lines)
