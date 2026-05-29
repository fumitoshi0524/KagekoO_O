"""Tool execution card — Rich Panel visualization for tool calls and results."""
from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from kageko.repl.diff import is_diff_output, render_diff_text

TOOL_ICONS = {
    "file_read": "\U0001f4c4",
    "file_write": "\U0001f4be",
    "file_list": "\U0001f4c2",
    "bash_run": "\U0001f4bb",
    "native_shell": "\U0001f4bb",
    "grep": "\U0001f50d",
    "ast_summarize": "\U0001f9e0",
    "echo": "\U0001f4e2",
    "todo_add": "➕",
    "todo_list": "\U0001f4cb",
}
DEFAULT_ICON = "⚙️"


def _icon_for(name: str) -> str:
    return TOOL_ICONS.get(name, DEFAULT_ICON)


def _truncate_value(value: Any, max_len: int = 200) -> str:
    s = str(value)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


def _format_args(args: dict[str, Any]) -> str:
    parts = []
    for k, v in args.items():
        parts.append(f"{k}={_truncate_value(v, 80)}")
    return ", ".join(parts)


def render_tool_call(
    console: Console,
    tool_name: str,
    args: dict[str, Any],
    status: str = "pending",
) -> None:
    icon = _icon_for(tool_name)
    border_style = "blue" if status == "pending" else "yellow"
    header = Text()
    header.append(f" {icon} ", style="bold")
    header.append(tool_name, style="bold white")
    args_text = Text(_format_args(args), style="dim")
    panel = Panel(args_text, title=header, title_align="left", border_style=border_style, padding=(0, 1))
    console.print(panel)


def render_tool_result(
    console: Console,
    tool_name: str,
    result: str,
    is_error: bool = False,
    max_lines: int = 30,
) -> None:
    icon = _icon_for(tool_name)
    border_style = "red" if is_error else "green"
    header = Text()
    header.append(f" {icon} ", style="bold")
    header.append(tool_name, style="bold white")
    if is_error:
        header.append(" [error]", style="bold red")
    else:
        header.append(" ✔", style="bold green")
    lines = result.split("\n")
    if len(lines) > max_lines:
        truncated = "\n".join(lines[:max_lines])
        truncated += f"\n... ({len(lines) - max_lines} more lines)"
    else:
        truncated = result
    content: Any
    # Check for diff output first
    if not is_error and is_diff_output(truncated):
        from io import StringIO
        buf = StringIO()
        diff_console = Console(file=buf, force_terminal=True, width=console.width)
        render_diff_text(diff_console, truncated)
        content = Text.from_ansi(buf.getvalue()) if buf.getvalue() else Text(truncated)
    else:
        try:
            json.loads(truncated)
            content = Syntax(truncated, "json", theme="monokai", word_wrap=True)
        except (json.JSONDecodeError, ValueError):
            content = Text(truncated, style="red" if is_error else "")
    panel = Panel(content, title=header, title_align="left", border_style=border_style, padding=(0, 1))
    console.print(panel)
