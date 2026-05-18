"""Configuration management commands."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from .._shared import console
from ..config import load_global_config, save_global_config
from ..setup import run_setup_wizard

config_app = typer.Typer(help="Manage configuration")


@config_app.command("init")
def config_init() -> None:
    """Initialize Kageko configuration interactively."""
    run_setup_wizard()


@config_app.command("get")
def config_get(key: Annotated[str, typer.Argument(help="Config key")]) -> None:
    config = load_global_config()
    value = config.get(key)
    console.print(f"[dim]{key}[/dim] = {'[dim]<not set>[/dim]' if value is None else str(value)}")


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Config key")],
    value: Annotated[str, typer.Argument(help="Config value")],
) -> None:
    config = load_global_config()
    parsed: object = value
    if value == "true":
        parsed = True
    elif value == "false":
        parsed = False
    elif value.isdigit():
        parsed = int(value)
    config[key] = parsed
    save_global_config(config)
    console.print(f"[bold green]✓[/bold green] {key} = {parsed}")


@config_app.command("list")
def config_list() -> None:
    config = load_global_config()
    if not config:
        console.print("[dim]No configuration set.[/dim]")
        return
    for k, v in sorted(config.items()):
        console.print(f"  [dim]{k}[/dim] = {json.dumps(v, ensure_ascii=False)}")
