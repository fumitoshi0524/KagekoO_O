"""Setup wizard for Kageko CLI."""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .config import load_global_config, save_global_config

console = Console()


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
    console.print("   You can now run [bold]kageko[/bold] without any arguments.\n")
    return provider, api_key
