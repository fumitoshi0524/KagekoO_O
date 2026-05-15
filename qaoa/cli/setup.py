"""Setup wizard for Kageko CLI."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box


console = Console()


def load_global_config() -> dict:
    path = Path.home() / ".kageko" / "config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_global_config(config: dict) -> None:
    path = Path.home() / ".kageko" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_setup_wizard() -> tuple[str, str]:
    console.print()
    console.print(Panel(
        "[bold cyan]Welcome to Kageko Agent CLI[/bold cyan]\n"
        "[dim]QAOA-powered tool-using assistant[/dim]\n\n"
        "Let's set up your LLM provider. You only need to do this once.\n"
        "Credentials are saved to [dim]~/.kageko/config.json[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))
    console.print("[bold]Supported providers:[/bold] openai, deepseek, claude, gemini")
    provider = Prompt.ask("Provider", default="openai").strip().lower() or "openai"
    while True:
        api_key = Prompt.ask(f"API key for [bold]{provider}[/bold]").strip()
        if api_key:
            break
        console.print("[yellow]API key is required.[/yellow] Press Ctrl+C to exit.")
    model = Prompt.ask("Model", default="").strip() or None
    config = load_global_config()
    config["provider"] = provider
    config["api_key"] = api_key
    if model:
        config["model"] = model
    save_global_config(config)
    console.print(f"\n[bold green]✓ Configuration saved[/bold green] to [dim]{Path.home() / '.kageko' / 'config.json'}[/dim]")
    console.print(f"   Provider: [bold]{provider}[/bold]")
    console.print(f"   You can now run [bold]kageko[/bold] without any arguments.\n")
    return provider, api_key
