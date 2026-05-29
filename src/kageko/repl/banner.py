"""Welcome banner component — oh-my-pi style box-drawing with O_O face."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text


def render_welcome(
    console: Console,
    model: str,
    provider: str,
    version: str,
) -> None:
    """Render the welcome banner on session start."""
    # Left column: O_O face integrated into name
    logo_lines = [
        r"                    ",
        r"    Ka( O_O )eko    ",
        r"      ^    ^        ",
        r"   looking at code  ",
        r"                    ",
    ]
    logo_text = Text("\n".join(logo_lines), style="bold cyan")

    # Right column: info
    info = Text()
    info.append("Welcome back!\n", style="bold")
    info.append("Model:    ", style="dim")
    info.append(f"{model}\n", style="bold white")
    info.append("Provider: ", style="dim")
    info.append(f"{provider}\n", style="white")
    info.append("Version:  ", style="dim")
    info.append(f"{version}\n", style="white")

    # Build panel content
    if console.width >= 60:
        columns = Columns([logo_text, info], padding=(2, 4), expand=False)
        console.print(Panel(columns, border_style="cyan", padding=(1, 2)))
    else:
        # Narrow terminal: single column, no logo
        console.print(Panel(info, border_style="cyan", padding=(1, 2)))

    # Tips
    console.print()
    tips = Text()
    tips.append("  Tips: ", style="bold dim")
    tips.append("/help", style="cyan")
    tips.append(" commands  |  ", style="dim")
    tips.append("/undo", style="cyan")
    tips.append(" undo  |  ", style="dim")
    tips.append("/retry", style="cyan")
    tips.append(" retry  |  ", style="dim")
    tips.append("/resume", style="cyan")
    tips.append(" sessions", style="dim")
    console.print(tips)
    console.print()
