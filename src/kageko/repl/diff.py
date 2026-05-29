"""Diff rendering — colored unified diffs with line numbers."""
from __future__ import annotations

import difflib
from rich.console import Console
from rich.text import Text


def render_diff(console: Console, old: str, new: str, filename: str = "") -> None:
    """Render a colored diff between old and new content."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}" if filename else "before",
        tofile=f"b/{filename}" if filename else "after",
    ))

    if not diff:
        console.print("[dim]No changes.[/]")
        return

    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            console.print(Text(line.rstrip(), style="bold"))
        elif line.startswith("@@"):
            console.print(Text(line.rstrip(), style="cyan"))
        elif line.startswith("+"):
            console.print(Text(line.rstrip(), style="green"))
        elif line.startswith("-"):
            console.print(Text(line.rstrip(), style="red"))
        else:
            console.print(Text(line.rstrip(), style="dim"))


def render_diff_text(console: Console, diff_text: str) -> None:
    """Render an existing unified diff string with colors."""
    if not diff_text:
        return
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            console.print(Text(line, style="bold"))
        elif line.startswith("@@"):
            console.print(Text(line, style="cyan"))
        elif line.startswith("+") and not line.startswith("+++"):
            console.print(Text(line, style="green"))
        elif line.startswith("-") and not line.startswith("---"):
            console.print(Text(line, style="red"))
        else:
            console.print(Text(line, style="dim"))


def is_diff_output(text: str) -> bool:
    """Detect if a tool result looks like a unified diff."""
    return (
        ("---" in text and "+++" in text and "@@" in text)
        or ("diff --git" in text)
    )
