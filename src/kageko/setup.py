"""Interactive setup wizard for first-time configuration."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

PROVIDERS = {
    "1": ("openai", "https://api.openai.com/v1", "OPENAI_API_KEY"),
    "2": ("ollama", "http://localhost:11434/v1", ""),
    "3": ("custom", "", ""),
}

SECURITY_MODES = {"1": "interactive", "2": "read-only", "3": "permissive"}


def run_setup() -> None:
    console = Console()
    console.print("[bold]Kageko Setup Wizard[/]\n")

    console.print("Select a provider:")
    console.print("  1) OpenAI")
    console.print("  2) Ollama (local)")
    console.print("  3) Custom endpoint")
    choice = Prompt.ask("Choice", choices=["1", "2", "3"], default="1")
    name, default_url, default_key_env = PROVIDERS[choice]

    base_url = default_url
    api_key_env = default_key_env

    if choice == "3":
        base_url = Prompt.ask("Base URL")
        api_key_env = Prompt.ask("API key env var (leave blank for literal key)", default="")

    api_key = ""
    if choice == "1" or (choice == "3" and api_key_env):
        api_key = Prompt.ask(
            f"API key (saved to ~/.kageko/.env as {api_key_env or 'KAGEKO_API_KEY'})",
            password=True,
        )
    elif choice == "3":
        api_key = Prompt.ask("API key (saved to ~/.kageko/.env)", password=True)

    default_models = {"1": "gpt-4o", "2": "llama3", "3": "gpt-4o"}
    model = Prompt.ask("Model", default=default_models[choice])

    console.print("\nSecurity mode:")
    console.print("  1) interactive  (ask before each tool call)")
    console.print("  2) read-only    (block writes)")
    console.print("  3) permissive   (run everything)")
    sec_choice = Prompt.ask("Choice", choices=["1", "2", "3"], default="1")
    sec_mode = SECURITY_MODES[sec_choice]

    config_dir = Path.home() / ".kageko"
    config_dir.mkdir(parents=True, exist_ok=True)

    toml_content = _build_toml(name, base_url, api_key_env, model, sec_mode)
    env_content = _build_env(api_key_env or "KAGEKO_API_KEY", api_key)

    (config_dir / "kageko.toml").write_text(toml_content)
    (config_dir / ".env").write_text(env_content)

    console.print(f"\n[green]Config saved to {config_dir / 'kageko.toml'}[/]")
    console.print(f"[green]API key saved to {config_dir / '.env'}[/]")
    console.print("\nRun [bold]kageko chat[/] to start.")


def _build_toml(provider_name: str, base_url: str, api_key_env: str, model: str, security_mode: str) -> str:
    lines = [f"[providers.{provider_name}]"]
    lines.append(f'base_url = "{base_url}"')
    if api_key_env:
        lines.append(f'api_key_env = "{api_key_env}"')
    lines.append("")
    lines.append("[agent]")
    lines.append(f'provider = "{provider_name}"')
    lines.append(f'model = "{model}"')
    lines.append("")
    lines.append("[security]")
    lines.append(f'mode = "{security_mode}"')
    lines.append("")
    lines.append("[database]")
    lines.append('path = "~/.kageko/kageko.db"')
    lines.append("")
    lines.append("[logging]")
    lines.append('level = "INFO"')
    lines.append("")
    return "\n".join(lines)


def _build_env(key_name: str, key_value: str) -> str:
    return f"{key_name}={key_value}\n"
