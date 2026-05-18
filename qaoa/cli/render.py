"""Rich rendering helpers for CLI output."""

from __future__ import annotations

import subprocess
from pathlib import Path

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

CATEGORY_COLORS = {
    "analysis": "blue",
    "operations": "yellow",
    "system": "magenta",
    "visualization": "green",
    "search": "cyan",
    "generate": "red",
}
RISK_COLORS = {"read": "green", "write": "yellow", "destructive": "red"}


def _get_git_info() -> str:
    """Return a short git status string, or '—' if not a git repo."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "—"

    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True, stderr=subprocess.DEVNULL,
        )
        dirty = len(status.strip().splitlines()) if status.strip() else 0
    except (OSError, subprocess.CalledProcessError):
        dirty = 0

    status_str = "clean" if dirty == 0 else f"{dirty} changed"
    return f"{branch}  ({status_str})"


def render_welcome(version="0.1.0", provider="?", model="?", tools=0,
                   skills=0, session="default", workspace="") -> Panel:
    """Render a project-context startup panel instead of ASCII art."""
    import os
    from rich.columns import Columns
    from rich.console import Group

    cwd = workspace or os.getcwd()
    home = os.path.expanduser("~")
    display_path = cwd
    if cwd.startswith(home):
        display_path = "~" + cwd[len(home):]

    git_info = _get_git_info()

    lines: list[Text | str] = []

    # Header
    header = Text()
    header.append("Kageko Agent", style="bold cyan")
    header.append(f"  v{version}", style="dim")
    lines.append(header)
    lines.append("")

    # Status fields
    fields = [
        ("Workspace", display_path),
        ("Git", git_info),
        ("Provider", f"{provider} / {model}" if model else provider),
        ("Tools", f"{tools} loaded"),
        ("Skills", f"{skills} available"),
        ("Session", session),
    ]
    for label, value in fields:
        label_text = Text()
        label_text.append(f"  {label:<12}", style="dim")
        label_text.append(value)
        lines.append(label_text)

    lines.append("")
    lines.append(Text("Type a task to begin.  /help for commands.", style="dim"))

    return Panel(
        Group(*lines),
        border_style="cyan",
        box=box.ROUNDED,
    )


def render_tool_table(specs, *, highlight: str = "") -> Table:
    table = Table(title="Available Tools", box=box.ROUNDED, highlight=True)
    table.add_column("Name", style="bold cyan", no_wrap=True)
    table.add_column("Category", style="italic")
    table.add_column("Domain")
    table.add_column("Risk", width=5)
    table.add_column("Description", max_width=50)
    for s in specs:
        cat_style = CATEGORY_COLORS.get(s.category, "white")
        risk_style = RISK_COLORS.get(s.risk_level, "white")
        name_style = "bold cyan" if highlight and highlight.lower() in s.name.lower() else "cyan"
        table.add_row(
            f"[{name_style}]{s.name}[/{name_style}]",
            f"[{cat_style}]{s.category}[/{cat_style}]",
            s.domain,
            f"[{risk_style}]⬤[/{risk_style}]",
            s.description[:80],
        )
    return table


def render_tool_detail(spec) -> Panel:
    cat_color = CATEGORY_COLORS.get(spec.category, "white")
    risk_color = RISK_COLORS.get(spec.risk_level, "white")
    body = (
        f"[bold]Name:[/bold] {spec.name}\n"
        f"[bold]Category:[/bold] [{cat_color}]{spec.category}[/{cat_color}]\n"
        f"[bold]Domain:[/bold] {spec.domain}\n"
        f"[bold]Risk:[/bold] [{risk_color}]{spec.risk_level}[/{risk_color}]\n"
        f"[bold]Input:[/bold] {spec.input_contract}\n"
        f"[bold]Output:[/bold] {spec.output_contract}\n"
        f"[bold]Tags:[/bold] {', '.join(spec.tags) if spec.tags else '—'}\n\n"
        f"[bold]Description:[/bold]\n{spec.description}"
    )
    return Panel(body, title=f"[bold]Tool: {spec.name}[/bold]", border_style=cat_color, box=box.ROUNDED)


def render_hud_prompt(provider="?", model="?", mode="default", session="?", msg_count=0) -> str:
    """Return a HUD-status REPL prompt string — plain text for prompt_toolkit."""
    short_session = session[:8] if session else "?"
    return (
        f"{provider}/{model or '?'}  {mode}  {short_session}  msgs:{msg_count}"
        f"\nkageko> "
    )


def render_skill_table(skills) -> Table:
    table = Table(title="Skills", box=box.ROUNDED)
    table.add_column("Name", style="bold green")
    table.add_column("Description", max_width=60)
    table.add_column("Tools")
    for s in skills:
        tools = getattr(s, 'tools', getattr(s, 'allowed_tools', []))
        table.add_row(s.name, s.description[:80] if s.description else "—",
                      ", ".join(tools) if tools else "—")
    return table
