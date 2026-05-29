"""Status line — turn count, tokens, model info bar."""
from __future__ import annotations

from rich.console import Console
from rich.text import Text


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}m"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def render_status_line(
    console: Console,
    turn: int,
    tokens: int,
    model: str,
    mode: str = "",
) -> None:
    line = Text()
    line.append("  ", style="")
    line.append("─" * min(console.width - 4, 60), style="dim")
    console.print(line)

    info = Text()
    info.append("  ", style="")
    info.append("Turn ", style="dim")
    info.append(str(turn), style="bold white")
    info.append("  │  ", style="dim")
    info.append("Tokens ", style="dim")
    info.append(_format_tokens(tokens), style="bold white")
    info.append("  │  ", style="dim")
    info.append("Model ", style="dim")
    info.append(model, style="cyan")
    if mode:
        info.append("  │  ", style="dim")
        info.append("Mode ", style="dim")
        info.append(mode, style="magenta")
    console.print(info)
    console.print()
