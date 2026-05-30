# src/kageko/cli.py
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import typer
from rich.console import Console

from kageko.agent.permissions import Decision, PermissionPipeline
from kageko.config import load_config
from kageko.repl.tool_card import render_tool_call, render_tool_result
from kageko.types import ToolCall

KNOWN_COMMANDS = {"chat", "tui", "version", "setup", "--help", "--version", "-h"}


def _rewrite_argv() -> None:
    """If first positional arg isn't a known command, prepend 'chat'."""
    if len(sys.argv) < 2:
        return
    first_arg = sys.argv[1]
    if first_arg.startswith("-"):
        return
    if first_arg in KNOWN_COMMANDS:
        return
    sys.argv.insert(1, "chat")

app = typer.Typer(
    name="kageko",
    help="Kageko — three-in-one AI agent (coding, general-purpose, research)",
)
console = Console()


@app.command()
def chat(
    query: list[str] = typer.Argument(None, help="Query to send directly"),
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

    # Initialize filesystem sandbox
    from kageko.tools.sandbox import set_workspace_root
    _ws_root = config.agent.workspace_root or str(Path.cwd())
    set_workspace_root(_ws_root)

    if query:
        asyncio.run(_single_query(config, " ".join(query)))
    else:
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
    from kageko.agent.delegate import make_delegate_handler
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

        from kageko.llm.providers import resolve_provider as _resolve_provider
        _provider = _resolve_provider(config.agent.provider) if config.agent.provider else None
        llm = LLMAdapter(
            model=config.agent.model,
            api_key=config.agent.api_key,
            base_url=config.agent.base_url,
            temperature=config.agent.temperature,
            provider=_provider,
        )

        registry = ToolRegistry()
        for t in BUILTIN_TOOLS:
            if t["fn"] is not None:
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
        permissions.prompt_fn = make_console_prompt_fn(permissions)

        engine = AgentEngine(
            llm=llm,
            tool_registry=registry,
            permissions=permissions,
            max_turns=config.agent.max_turns,
            system_prompt=config.agent.system_prompt or "You are Kageko, a helpful AI assistant.",
            context_window_size=config.agent.get_context_window_size(),
        )

        # Wire up delegate tool after engine creation
        delegate_handler = make_delegate_handler(engine)
        registry.register(Tool(
            name="delegate",
            description="Delegate a task to a subagent. Use for parallel work or isolated subtasks.",
            parameters={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The task to delegate to the subagent"},
                    "allowed_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tool names the subagent can use",
                    },
                    "max_turns": {"type": "integer", "description": "Max turns for the subagent (default 10)", "default": 10},
                },
                "required": ["task"],
            },
            handler=delegate_handler,
            category="agent",
        ))

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


@app.command()
def setup() -> None:
    """Interactive setup wizard for first-time configuration."""
    from kageko.setup import run_setup
    run_setup()


def _select_menu(options: list[tuple[str, str, str]]) -> int | None:
    """Show an arrow-key navigable menu. Returns selected index or None on cancel.

    Each option is (key, label, style). Blocks until Enter or Esc.
    """
    import sys

    # Read a single keystroke, handling arrow-key escape sequences
    def _getch() -> str:
        if sys.platform == "win32":
            import msvcrt
            ch = msvcrt.getwch()
            if ch == "\x00" or ch == "\xe0":
                ch = msvcrt.getwch()
                if ch == "H": return "up"
                if ch == "P": return "down"
                return ch
            if ch == "\r": return "enter"
            if ch == "\x1b": return "esc"
            return ch
        else:
            import termios, tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    seq = sys.stdin.read(2)
                    if seq == "[A": return "up"
                    if seq == "[B": return "down"
                    return "esc"
                if ch == "\r": return "enter"
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner

    selected = 0
    result: int | None = None

    def _render(sel: int) -> Text:
        out = Text()
        for i, (key, label, style) in enumerate(options):
            prefix = "▶" if i == sel else " "
            line_style = style if i == sel else "dim"
            out.append(f" {prefix} ", style="bold yellow" if i == sel else "dim")
            out.append(f"{label}", style=line_style)
            if i < len(options) - 1:
                out.append("\n")
        out.append("\n")
        out.append("  ↑↓ move  Enter select  Esc cancel", style="dim italic")
        return out

    with Live(_render(selected), console=console, transient=True, auto_refresh=False) as live:
        while result is None:
            key = _getch()
            if key == "up":
                selected = (selected - 1) % len(options)
            elif key == "down":
                selected = (selected + 1) % len(options)
            elif key == "enter":
                result = selected
            elif key == "esc":
                result = None
                break
            live.update(_render(selected), refresh=True)

    return result


def make_console_prompt_fn(permissions: "PermissionPipeline"):
    """Return a prompt function with arrow-key menu and session-wide 'always' memory."""
    from kageko.agent.permissions import Decision
    from rich.panel import Panel
    from rich.text import Text

    async def _prompt(tool_call: ToolCall) -> Decision:
        if tool_call.name in permissions._session_allow_all:
            return Decision.ALLOW

        args_str = ", ".join(f"{k}={v!r}" for k, v in tool_call.args.items())
        body = Text()
        body.append("Tool: ", style="bold yellow")
        body.append(tool_call.name, style="bold cyan")
        body.append(f"\nArgs: ", style="dim")
        body.append(args_str[:200], style="white")

        console.print()
        console.print(Panel(body, border_style="yellow", title="Permission Required", title_align="left"))

        options = [
            ("a", "Always allow (rest of session)", "bold green"),
            ("y", "Allow once", "green"),
            ("n", "Deny", "bold red"),
        ]

        loop = asyncio.get_event_loop()
        idx = await loop.run_in_executor(None, lambda: _select_menu(options))

        if idx is None or idx == 2:  # Esc or Deny
            console.print(f"[red]Denied '{tool_call.name}'[/]")
            return Decision.DENY
        if idx == 0:  # Always
            permissions.allow_always(tool_call.name)
            console.print(f"[green]Always allowing '{tool_call.name}'[/]")
        return Decision.ALLOW

    return _prompt


async def _single_query(config, query: str) -> None:
    from kageko.agent.delegate import make_delegate_handler
    from kageko.agent.loop import AgentEngine
    from kageko.agent.permissions import PermissionPipeline, SecurityMode
    from kageko.data.db import KagekoDB
    from kageko.learning.memory import MemoryManager
    from kageko.llm import LLMAdapter
    from kageko.tools.registry import ToolRegistry, Tool
    from kageko.tools.builtin import BUILTIN_TOOLS
    from kageko.tools.mcp_client import MCPClient
    from kageko.types import AgentMode, Message
    from kageko.repl.stream import StreamHandler
    from kageko.repl.status import render_status_line
    from kageko.repl.renderer import render_markdown

    logging.basicConfig(level=getattr(logging, config.logging.level.upper(), logging.INFO))

    db = KagekoDB(config.database.path)
    await db.init()

    memory_mgr = MemoryManager(db)

    from kageko.llm.providers import resolve_provider as _resolve_provider
    _provider = _resolve_provider(config.agent.provider) if config.agent.provider else None
    llm = LLMAdapter(
        model=config.agent.model,
        api_key=config.agent.api_key,
        base_url=config.agent.base_url,
        temperature=config.agent.temperature,
        provider=_provider,
    )

    registry = ToolRegistry()
    for t in BUILTIN_TOOLS:
        if t["fn"] is not None:
            registry.register(Tool(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
                handler=t["fn"],
                category=t["category"],
            ))

    # Connect MCP servers
    mcp_client = None
    if config.mcp_servers:
        mcp_client = MCPClient(servers=list(config.mcp_servers.values()))
        await mcp_client.connect_all()
        for tool_info in mcp_client.get_all_tools():
            registry.register(Tool(
                name=tool_info["name"],
                description=tool_info["description"],
                parameters=tool_info["parameters"],
                handler=mcp_client.get_tool_handler(tool_info["_mcp_server"], tool_info["name"]),
                category="mcp",
            ))

    permissions = PermissionPipeline(
        mode=SecurityMode(config.security.mode),
        sandbox_enabled=config.security.sandbox,
    )
    permissions.prompt_fn = make_console_prompt_fn(permissions)

    async def on_tool_start(name, args):
        render_tool_call(console, name, args, status="pending")

    async def on_tool_end(name, result, is_error):
        render_tool_result(console, name, result, is_error=is_error)

    system_prompt = config.agent.system_prompt or "You are Kageko, a helpful AI assistant."
    memory_snapshot = await memory_mgr.load_snapshot()
    if memory_snapshot:
        system_prompt = (
            system_prompt
            + "\n\n[Long-term memory — facts from past sessions]\n"
            + memory_snapshot
        )

    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=config.agent.max_turns,
        system_prompt=system_prompt,
        context_window_size=config.agent.get_context_window_size(),
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        memory=memory_mgr,
    )

    # Wire up delegate tool after engine creation
    delegate_handler = make_delegate_handler(engine)
    registry.register(Tool(
        name="delegate",
        description="Delegate a task to a subagent. Use for parallel work or isolated subtasks.",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The task to delegate to the subagent"},
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of tool names the subagent can use",
                },
                "max_turns": {"type": "integer", "description": "Max turns for the subagent (default 10)", "default": 10},
            },
            "required": ["task"],
        },
        handler=delegate_handler,
        category="agent",
    ))

    messages = [Message(role="user", content=query)]
    stream = StreamHandler(console)
    stream.start_spinner("Thinking...")
    assistant_text = ""
    total_tokens = 0
    try:
        async for tok in engine.run_stream(messages, mode=AgentMode(config.agent.mode)):
            if hasattr(tok, "text") and tok.text:
                stream.on_token(tok.text)
                assistant_text += tok.text
        stream.finish()
    except Exception:
        stream.stop_spinner()
        console.print("[dim]Stream interrupted, retrying...[/]")
        with console.status("Thinking..."):
            async for tok in engine.run_stream(messages, mode=AgentMode(config.agent.mode)):
                if hasattr(tok, "text") and tok.text:
                    assistant_text += tok.text

    render_status_line(
        console,
        turn=1,
        tokens=engine.last_tokens,
        model=config.agent.model,
        mode=config.agent.mode,
    )
    # Single-shot: still nudge so facts accumulate across invocations
    if memory_mgr.nudge():
        import asyncio as _asyncio
        _asyncio.create_task(
            memory_mgr.run_review(messages, llm),
            name="kageko-nudge-review",
        )
    if mcp_client:
        await mcp_client.disconnect_all()
    await db.close()


async def _interactive_chat(config) -> None:
    from kageko.agent.delegate import make_delegate_handler
    from kageko.agent.loop import AgentEngine
    from kageko.agent.permissions import PermissionPipeline, SecurityMode
    from kageko.agent.ttsr import Correction
    from kageko.data.db import KagekoDB
    from kageko.learning.memory import MemoryManager
    from kageko.llm import LLMAdapter
    from kageko.tools.registry import ToolRegistry, Tool
    from kageko.tools.builtin import BUILTIN_TOOLS
    from kageko.tools.mcp_client import MCPClient
    from kageko.types import AgentMode, Message

    logging.basicConfig(level=getattr(logging, config.logging.level.upper(), logging.INFO))

    db = KagekoDB(config.database.path)
    await db.init()

    # Memory manager with Hermes-style Nudge Engine
    memory_mgr = MemoryManager(db)

    # Create DB session for this chat
    import uuid
    session_chat_id = uuid.uuid4().hex[:12]
    session = await db.create_session(platform="cli", chat_id=session_chat_id)

    from kageko.llm.providers import resolve_provider as _resolve_provider
    _provider = _resolve_provider(config.agent.provider) if config.agent.provider else None
    llm = LLMAdapter(
        model=config.agent.model,
        api_key=config.agent.api_key,
        base_url=config.agent.base_url,
        temperature=config.agent.temperature,
        provider=_provider,
    )

    registry = ToolRegistry()
    for t in BUILTIN_TOOLS:
        if t["fn"] is not None:
            registry.register(Tool(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
                handler=t["fn"],
                category=t["category"],
            ))

    # Connect MCP servers
    mcp_client = None
    if config.mcp_servers:
        mcp_client = MCPClient(servers=list(config.mcp_servers.values()))
        await mcp_client.connect_all()
        for tool_info in mcp_client.get_all_tools():
            registry.register(Tool(
                name=tool_info["name"],
                description=tool_info["description"],
                parameters=tool_info["parameters"],
                handler=mcp_client.get_tool_handler(tool_info["_mcp_server"], tool_info["name"]),
                category="mcp",
            ))

    permissions = PermissionPipeline(
        mode=SecurityMode(config.security.mode),
        sandbox_enabled=config.security.sandbox,
    )
    permissions.prompt_fn = make_console_prompt_fn(permissions)

    # Build default system prompt if none configured.
    # If we have memories from previous sessions, freeze a snapshot and
    # inject it once (Hermes-style — preserves prefix caching).
    system_prompt = config.agent.system_prompt or "You are Kageko, a helpful AI assistant."
    memory_snapshot = await memory_mgr.load_snapshot()
    if memory_snapshot:
        system_prompt = (
            system_prompt
            + "\n\n[Long-term memory — facts from past sessions]\n"
            + memory_snapshot
        )

    async def on_tool_start(name, args):
        render_tool_call(console, name, args, status="pending")

    async def on_tool_end(name, result, is_error):
        render_tool_result(console, name, result, is_error=is_error)

    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=config.agent.max_turns,
        system_prompt=system_prompt,
        context_window_size=config.agent.get_context_window_size(),
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        memory=memory_mgr,
    )

    # Wire up delegate tool after engine creation
    delegate_handler = make_delegate_handler(engine)
    registry.register(Tool(
        name="delegate",
        description="Delegate a task to a subagent. Use for parallel work or isolated subtasks.",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The task to delegate to the subagent"},
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of tool names the subagent can use",
                },
                "max_turns": {"type": "integer", "description": "Max turns for the subagent (default 10)", "default": 10},
            },
            "required": ["task"],
        },
        handler=delegate_handler,
        category="agent",
    ))

    from kageko.cli_commands import ModeRef, SlashCommands
    from kageko.repl.banner import render_welcome
    from kageko.repl.stream import StreamHandler
    from kageko.repl.status import render_status_line
    from kageko.repl.renderer import render_markdown
    from kageko.repl.prompt import create_repl_session
    import kageko

    mode = ModeRef(AgentMode(config.agent.mode))

    render_welcome(
        console,
        model=config.agent.model,
        provider=config.agent.provider or "openai",
        version=kageko.__version__,
    )

    messages: list[Message] = []
    sc = SlashCommands(console, messages, mode, db=db, session=session, tool_registry=registry, config=config, engine=engine)

    repl_session = create_repl_session(
        slash_commands=list(sc._commands.keys()),
    )

    while True:
        try:
            user_input = await repl_session.prompt_async("> ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye![/]")
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

        # Auto-title: set session title from first user message
        if len([m for m in messages if m.role == "user"]) == 1:
            title = user_input.strip()[:50]
            await db.set_session_title(session.id, title)

        assistant_text = ""
        total_tokens = 0

        stream = StreamHandler(console)
        stream.start_spinner("Thinking...")

        try:
            async for tok in engine.run_stream(messages, mode=mode.mode):
                if isinstance(tok, Correction):
                    stream.stop_spinner()
                    console.print(f"\n[bold red][TTSR][/]: {tok.message}")
                    break
                if hasattr(tok, "text") and tok.text:
                    stream.on_token(tok.text)
                    assistant_text += tok.text
            stream.finish()
        except Exception:
            stream.stop_spinner()
            console.print("[dim]Stream interrupted, retrying...[/]")
            with console.status("Thinking..."):
                async for tok in engine.run_stream(messages, mode=mode.mode):
                    if hasattr(tok, "text") and tok.text:
                        assistant_text += tok.text

        # Append assistant reply to history and persist to DB
        # The engine already appended the assistant message to messages with
        # reasoning_content, tool_calls, etc. — use that instead of a bare duplicate.
        if messages and messages[-1].role == "assistant":
            last = messages[-1]
            await db.append_message(
                session.id, role="assistant", content=last.content,
                reasoning_content=last.reasoning_content or "",
            )
        else:
            messages.append(Message(role="assistant", content=assistant_text))
            await db.append_message(session.id, role="assistant", content=assistant_text)

        render_status_line(
            console,
            turn=len([m for m in messages if m.role == "user"]),
            tokens=engine.last_tokens,
            model=config.agent.model,
            mode=mode.mode.value,
        )

        # Hermes-style Nudge Engine: every ~N turns, ask the LLM to extract
        # declarative facts in the background (never blocks the user).
        if memory_mgr.nudge():
            import asyncio as _asyncio
            _asyncio.create_task(
                memory_mgr.run_review(messages, llm),
                name="kageko-nudge-review",
            )

    if mcp_client:
        await mcp_client.disconnect_all()
    await db.close()


def main() -> None:
    _rewrite_argv()
    app()


if __name__ == "__main__":
    main()
