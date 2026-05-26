# src/kageko/cli.py
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console

from kageko.config import load_config

app = typer.Typer(
    name="kageko",
    help="Kageko — three-in-one AI agent (coding, general-purpose, research)",
)
console = Console()


@app.command()
def chat(
    config_path: str = typer.Option(None, "--config", "-c", help="Path to kageko.toml"),
    model: str = typer.Option(None, "--model", "-m", help="Override model"),
    mode: str = typer.Option(None, "--mode", help="Agent mode: tool-use or qaoa"),
) -> None:
    """Start an interactive chat session."""
    config = load_config(config_path)
    if model:
        config.agent.model = model
    if mode:
        config.agent.mode = mode

    asyncio.run(_interactive_chat(config))


@app.command()
def tui(
    config_path: str = typer.Option(None, "--config", "-c", help="Path to kageko.toml"),
    model: str = typer.Option(None, "--model", "-m", help="Override model"),
    mode: str = typer.Option(None, "--mode", help="Agent mode: tool-use or qaoa"),
) -> None:
    """Start the Textual TUI interface."""
    config = load_config(config_path)
    if model:
        config.agent.model = model
    if mode:
        config.agent.mode = mode

    from kageko.tui.app import KagekoTUI
    from kageko.agent.loop import AgentEngine
    from kageko.agent.permissions import PermissionPipeline, SecurityMode
    from kageko.data.db import KagekoDB
    from kageko.llm import LLMAdapter
    from kageko.tools.registry import ToolRegistry, Tool
    from kageko.tools.builtin import BUILTIN_TOOLS
    from kageko.types import AgentMode

    async def setup_and_run():
        logging.basicConfig(level=getattr(logging, config.logging.level.upper(), logging.INFO))

        db = KagekoDB(config.database.path)
        await db.init()

        llm = LLMAdapter(
            model=config.agent.model,
            api_key=config.agent.api_key,
            base_url=config.agent.base_url,
        )

        registry = ToolRegistry()
        for t in BUILTIN_TOOLS:
            registry.register(Tool(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
                handler=t["fn"],
                category=t["category"],
            ))

        permissions = PermissionPipeline(
            mode=SecurityMode(config.security.mode),
            sandbox_enabled=config.security.sandbox,
        )

        engine = AgentEngine(
            llm=llm,
            tool_registry=registry,
            permissions=permissions,
            max_turns=config.agent.max_turns,
        )

        agent_mode = AgentMode(config.agent.mode)
        tui_app = KagekoTUI(engine=engine, mode=agent_mode)
        tui_app.run()
        await db.close()

    asyncio.run(setup_and_run())


@app.command()
def version() -> None:
    """Print version."""
    import kageko
    console.print(f"Kageko v{kageko.__version__}")


async def _interactive_chat(config) -> None:
    from kageko.agent.loop import AgentEngine
    from kageko.agent.permissions import PermissionPipeline, SecurityMode
    from kageko.agent.ttsr import Correction
    from kageko.data.db import KagekoDB
    from kageko.llm import LLMAdapter
    from kageko.tools.registry import ToolRegistry, Tool
    from kageko.tools.builtin import BUILTIN_TOOLS
    from kageko.types import AgentMode

    logging.basicConfig(level=getattr(logging, config.logging.level.upper(), logging.INFO))

    db = KagekoDB(config.database.path)
    await db.init()

    llm = LLMAdapter(
        model=config.agent.model,
        api_key=config.agent.api_key,
        base_url=config.agent.base_url,
    )

    registry = ToolRegistry()
    for t in BUILTIN_TOOLS:
        registry.register(Tool(
            name=t["name"],
            description=t["description"],
            parameters=t["parameters"],
            handler=t["fn"],
            category=t["category"],
        ))

    permissions = PermissionPipeline(
        mode=SecurityMode(config.security.mode),
        sandbox_enabled=config.security.sandbox,
    )

    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=config.agent.max_turns,
    )

    mode = AgentMode(config.agent.mode)

    console.print(f"[bold green]Kageko[/] — model={config.agent.model} mode={mode.value}")
    console.print("Type your message, or 'quit' to exit.\n")

    while True:
        try:
            user_input = console.input("[bold blue]>[/] ")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() in ("quit", "exit", "q"):
            break
        if not user_input.strip():
            continue

        try:
            console.print()
            async for tok in engine.run_stream(user_input.strip(), mode=mode):
                if isinstance(tok, Correction):
                    console.print(f"\n[bold red][TTSR][/]: {tok.message}")
                    break
                if hasattr(tok, "text") and tok.text:
                    console.print(tok.text, end="")
            console.print()
        except Exception:
            with console.status("Thinking..."):
                result = await engine.run(user_input.strip(), mode=mode)
            console.print(f"\n{result.answer}\n")
    await db.close()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
