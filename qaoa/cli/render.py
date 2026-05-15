"""Rich rendering helpers for CLI output."""

from __future__ import annotations

from rich.table import Table
from rich.panel import Panel
from rich import box


CATEGORY_COLORS = {
    "analysis": "blue",
    "operations": "yellow",
    "system": "magenta",
    "visualization": "green",
    "search": "cyan",
    "generate": "red",
}
RISK_COLORS = {"read": "green", "write": "yellow", "destructive": "red"}


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
