# src/kageko/cli.py
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console

from kageko.agent.permissions import Decision, PermissionPipeline, SecurityMode
from kageko.config import load_config
from kageko.types import ToolCall

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
            prompt_fn=console_prompt_fn,
            sandbox_enabled=config.security.sandbox,
        )

        engine = AgentEngine(
            llm=llm,
            tool_registry=registry,
            permissions=permissions,
            max_turns=config.agent.max_turns,
            system_prompt=config.agent.system_prompt or "You are Kageko, a helpful AI assistant.",
        )

        import uuid
        agent_mode = AgentMode(config.agent.mode)
        session_chat_id = uuid.uuid4().hex[:12]
        session = await db.create_session(platform="tui", chat_id=session_chat_id)
        tui_app = KagekoTUI(engine=engine, mode=agent_mode, db=db, session=session)
        tui_app.run()
        await db.close()

    asyncio.run(setup_and_run())


@app.command()
def version() -> None:
    """Print version."""
    import kageko
    console.print(f"Kageko v{kageko.__version__}")


async def console_prompt_fn(tool_call: ToolCall) -> Decision:
    console.print(f"\n[yellow]Tool:[/] {tool_call.name}({tool_call.args})")
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None, lambda: console.input("[yellow]Allow? [y/n/a]:[/] ").strip().lower()
    )
    if answer in ("y", "yes", "a", "always"):
        return Decision.ALLOW
    return Decision.DENY


async def _interactive_chat(config) -> None:
    from kageko.agent.loop import AgentEngine
    from kageko.agent.permissions import PermissionPipeline, SecurityMode
    from kageko.agent.ttsr import Correction
    from kageko.data.db import KagekoDB
    from kageko.llm import LLMAdapter
    from kageko.tools.registry import ToolRegistry, Tool
    from kageko.tools.builtin import BUILTIN_TOOLS
    from kageko.types import AgentMode, Message

    logging.basicConfig(level=getattr(logging, config.logging.level.upper(), logging.INFO))

    db = KagekoDB(config.database.path)
    await db.init()

    # Create DB session for this chat
    import uuid
    session_chat_id = uuid.uuid4().hex[:12]
    session = await db.create_session(platform="cli", chat_id=session_chat_id)

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
        prompt_fn=console_prompt_fn,
        sandbox_enabled=config.security.sandbox,
    )

    # Build default system prompt if none configured
    system_prompt = config.agent.system_prompt or "You are Kageko, a helpful AI assistant."

    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=config.agent.max_turns,
        system_prompt=system_prompt,
    )

    from kageko.cli_commands import ModeRef, SlashCommands

    mode = ModeRef(AgentMode(config.agent.mode))

    console.print(f"[bold green]Kageko[/] — model={config.agent.model} mode={mode.value}")
    console.print("Type your message, or 'quit' to exit.\n")

    messages: list[Message] = []
    sc = SlashCommands(console, messages, mode, db=db, session=session)

    while True:
        try:
            user_input = console.input("[bold blue]>[/] ")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.strip().lower() in ("quit", "exit", "q"):
            break
        if not user_input.strip():
            continue

        # Handle slash commands
        if sc.handle(user_input.strip()):
            continue

        # Append user message to history and persist to DB
        messages.append(Message(role="user", content=user_input.strip()))
        await db.append_message(session.id, role="user", content=user_input.strip())

        assistant_text = ""

        try:
            console.print()
            async for tok in engine.run_stream(messages, mode=mode.mode):
                if isinstance(tok, Correction):
                    console.print(f"\n[bold red][TTSR][/]: {tok.message}")
                    break
                if hasattr(tok, "text") and tok.text:
                    console.print(tok.text, end="")
                    assistant_text += tok.text
            console.print()
        except Exception:
            with console.status("Thinking..."):
                result = await engine.run(messages, mode=mode.mode)
            assistant_text = result.answer
            console.print(f"\n{result.answer}\n")

        # Append assistant reply to history and persist to DB
        messages.append(Message(role="assistant", content=assistant_text))
        await db.append_message(session.id, role="assistant", content=assistant_text)

    await db.close()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
