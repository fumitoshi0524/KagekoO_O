"""Slash commands for the interactive CLI REPL."""
from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console
from rich.table import Table

from kageko.types import AgentMode, Message


async def _interactive_pick(items: list[str], title: str = "") -> int | None:
    """Arrow-key interactive picker. Returns selected index or None if cancelled."""
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style

    cursor = [0]  # mutable so closures can modify it

    def get_menu_text():
        lines = []
        if title:
            lines.append(("class:title", f"  {title}\n"))
            lines.append(("", "\n"))
        for i, item in enumerate(items):
            if i == cursor[0]:
                lines.append(("class:selected", f"  > {item}\n"))
            else:
                lines.append(("", f"    {item}\n"))
        lines.append(("", "\n"))
        lines.append(("class:hint", "  ↑/↓ navigate  Enter select  Esc cancel"))
        return lines

    style = Style.from_dict({
        "selected": "bold cyan",
        "title": "bold",
        "hint": "dim",
    })

    control = FormattedTextControl(get_menu_text)
    layout = Layout(HSplit([Window(content=control)]))

    kb = KeyBindings()

    @kb.add("up")
    def _(event):
        cursor[0] = max(0, cursor[0] - 1)

    @kb.add("down")
    def _(event):
        cursor[0] = min(len(items) - 1, cursor[0] + 1)

    @kb.add("enter")
    def _(event):
        event.app.exit(result=cursor[0])

    @kb.add("escape")
    @kb.add("c-c")
    def _(event):
        event.app.exit(result=None)

    app: Application[int | None] = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        mouse_support=False,
        full_screen=False,
    )
    return await app.run_async()


class ModeRef:
    """Mutable wrapper around an AgentMode enum value.

    Needed because enums are immutable and reassigning a local variable
    inside ``SlashCommands`` would not propagate to the caller.
    """

    def __init__(self, mode: AgentMode) -> None:
        self._mode = mode

    @property
    def value(self) -> str:
        return self._mode.value

    @property
    def mode(self) -> AgentMode:
        return self._mode

    @mode.setter
    def mode(self, m: AgentMode) -> None:
        self._mode = m


class SlashCommands:
    """Handle slash commands typed in the REPL.

    Parameters
    ----------
    console : Console
        Rich console for output.
    messages : list[Message]
        The in-memory conversation history (mutated by /clear).
    mode : ModeRef
        Mutable reference to the current agent mode.
    db : KagekoDB or None
        Database handle for /resume.
    session : SessionRecord or None
        Current session record for /session.
    """

    def __init__(
        self,
        console: Console,
        messages: list[Message],
        mode: ModeRef,
        db: Any = None,
        session: Any = None,
        tool_registry: Any = None,
        config: Any = None,
    ) -> None:
        self.console = console
        self.messages = messages
        self.mode = mode
        self.db = db
        self.session = session
        self.tool_registry = tool_registry
        self.config = config
        self.memory = None  # will be set by cli.py if available

        self._commands: dict[str, Any] = {
            "/help": self._help,
            "/clear": self._clear,
            "/mode": self._mode_cmd,
            "/history": self._history,
            "/resume": self._resume,
            "/tools": self._tools,
            "/model": self._model,
            "/undo": self._undo,
            "/retry": self._retry,
            "/resume": self._resume,
            "/config": self._config,
            "/search": self._search,
        }

    # ---- public API -------------------------------------------------------

    def handle(self, text: str) -> bool:
        """Process *text* as a slash command.

        Returns ``True`` if the input was consumed (i.e. it started with ``/``),
        ``False`` otherwise so the caller can pass it to the engine.
        """
        if not text.startswith("/"):
            return False

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = self._commands.get(cmd)
        if handler:
            handler(args)
            return True

        self.console.print(f"[red]Unknown command: {cmd}[/]")
        return True

    # ---- individual commands ----------------------------------------------

    def _help(self, args: str) -> None:
        """Show available commands, optionally grouped by category."""
        if args.strip():
            # Show help for a specific command
            cmd_name = args.strip()
            if not cmd_name.startswith("/"):
                cmd_name = "/" + cmd_name
            if cmd_name in self._commands:
                handler = self._commands[cmd_name]
                doc = handler.__doc__ or "No description."
                self.console.print(f"[bold]{cmd_name}[/] — {doc}")
            else:
                self.console.print(f"[red]Unknown command: {cmd_name}[/]")
            return

        self.console.print("[bold]Kageko Commands[/]\n")

        categories = {
            "Session": [
                ("/help [CMD]", "Show this help or details for a command"),
                ("/clear", "Clear conversation history"),
                ("/undo", "Remove last user+assistant exchange"),
                ("/retry", "Remove last assistant reply for re-generation"),
                ("/resume [N|ID]", "Show sessions and pick one to resume"),
                ("/history [N]", "Show last N messages (default 10)"),
                ("/search <Q>", "Search memory and sessions"),
            ],
            "Tools & Models": [
                ("/tools", "List all available tools"),
                ("/model [NAME]", "Show current model or switch to another"),
                ("/mode [MODE]", "Show or switch agent mode (tool-use / qaoa)"),
            ],
            "Info": [
                ("/config", "Show current configuration"),
            ],
        }

        for category, cmds in categories.items():
            self.console.print(f"[bold magenta]{category}[/]")
            for name, desc in cmds:
                self.console.print(f"  [cyan]{name:<22}[/] {desc}")
            self.console.print()

    def _tools(self, _args: str) -> None:
        """List all available tools in a Rich Table."""
        if not self.tool_registry:
            self.console.print("[dim]No tool registry available.[/]")
            return

        tools = self.tool_registry.list()
        if not tools:
            self.console.print("[dim]No tools registered.[/]")
            return

        table = Table(title="Available Tools")
        table.add_column("Name", style="cyan bold")
        table.add_column("Category", style="magenta")
        table.add_column("Description")
        table.add_column("Parameters", style="dim", max_width=40)

        for tool in tools:
            # Extract parameter names from schema
            params = tool.parameters or {}
            props = params.get("properties", {})
            required = set(params.get("required", []))
            param_parts = []
            for pname, pinfo in props.items():
                ptype = pinfo.get("type", "any")
                marker = "" if pname in required else "?"
                param_parts.append(f"{pname}{marker}: {ptype}")
            param_str = ", ".join(param_parts) if param_parts else "—"

            table.add_row(
                tool.name,
                tool.category or "general",
                (tool.description or "")[:60],
                param_str,
            )

        self.console.print(table)
        self.console.print(f"\n[dim]{len(tools)} tools available[/]")

    def _model(self, args: str) -> None:
        """Show current model or switch to a different one."""
        if not self.config:
            self.console.print("[dim]No config available.[/]")
            return

        if not args.strip():
            # Show current model info
            self.console.print(f"  Current model: [bold cyan]{self.config.agent.model}[/]")
            self.console.print(f"  Base URL:      {self.config.agent.base_url}")
            self.console.print(f"  Temperature:   {self.config.agent.temperature}")
            if self.config.agent.provider:
                self.console.print(f"  Provider:      {self.config.agent.provider}")
            return

        # Switch model
        new_model = args.strip()
        old_model = self.config.agent.model
        self.config.agent.model = new_model
        self.console.print(f"Model switched: [dim]{old_model}[/] → [bold cyan]{new_model}[/]")
        self.console.print("[dim]Note: model change takes effect on next LLM call.[/]")

    def _config(self, _args: str) -> None:
        """Show current configuration and enter interactive edit mode."""
        if not self.config:
            self.console.print("[dim]No config available.[/]")
            return

        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside the async REPL — schedule on the existing loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(asyncio.run, self._config_interactive()).result()
        else:
            # Standalone invocation
            try:
                asyncio.run(self._config_interactive())
            except Exception:
                self._show_config_table()

    async def _config_interactive(self) -> None:
        """Interactive config editor with arrow-key picker."""
        from kageko.config import save_config

        while True:
            self._show_config_table()

            fields = self._config_fields()
            labels = [f"{f['label']:30s} {f['current']}" for f in fields]
            labels.append("  Done (Esc)")

            try:
                idx = await _interactive_pick(labels, title="Edit setting")
            except Exception:
                # No TTY available (e.g. test environment) — show table only
                return
            if idx is None or idx == len(fields):
                break

            field_info = fields[idx]
            self.console.print(f"\n  [cyan]{field_info['label']}[/]  [dim]current: {field_info['current']}[/]")

            # Prompt for new value
            is_secret = field_info.get("secret", False)
            new_val = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.console.input("  New value: ", password=is_secret).strip()
            )

            if not new_val:
                self.console.print("[dim]Skipped.[/]")
                continue

            coerced = self._coerce_value(new_val, field_info.get("vtype", "str"))
            if coerced is None:
                self.console.print(f"  [red]Invalid value for {field_info['vtype']} type[/]\n")
                continue

            obj = getattr(self.config, field_info["section"])
            setattr(obj, field_info["key"], coerced)

            path = save_config(self.config)
            self.console.print(f"  [green]Updated {field_info['section']}.{field_info['key']} = {coerced}[/]")
            self.console.print(f"  [dim]Saved to {path}[/]\n")

    @staticmethod
    def _mask_secret(val: str) -> str:
        """Mask a secret value for display: show first 4 and last 4 chars."""
        if not val or len(val) <= 8:
            return val
        return f"{val[:4]}****{val[-4:]}"

    def _config_fields(self) -> list[dict]:
        """Build list of editable config fields."""
        fields = []

        def _add(section, key, vtype="str", secret=False):
            raw = getattr(getattr(self.config, section), key)
            if vtype == "bool":
                display = "true" if raw else "false"
            elif secret:
                display = self._mask_secret(str(raw))
            else:
                display = str(raw)
            fields.append({
                "section": section, "key": key,
                "label": f"{section}.{key}",
                "current": display,
                "vtype": vtype,
                "secret": secret,
            })

        _add("agent", "model")
        _add("agent", "mode")
        _add("agent", "base_url")
        _add("agent", "api_key", secret=True)
        _add("agent", "temperature", "float")
        _add("agent", "context_window_size", "int")
        _add("agent", "max_turns", "int")
        _add("agent", "system_prompt")
        _add("agent", "provider")

        _add("security", "mode")
        _add("security", "sandbox", vtype="bool")
        _add("database", "path")
        _add("logging", "level")
        return fields

    @staticmethod
    def _coerce_value(raw: str, vtype: str) -> str | int | float | bool | None:
        """Coerce a string input to the target type. Returns None on failure."""
        if vtype == "bool":
            return raw.lower() in ("true", "1", "yes", "on")
        if vtype == "int":
            try:
                return int(raw)
            except ValueError:
                return None
        if vtype == "float":
            try:
                return float(raw)
            except ValueError:
                return None
        return raw

    def _show_config_table(self) -> None:
        """Display the current configuration as a Rich table."""
        table = Table(title="Configuration")
        table.add_column("Section", style="bold")
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        for field_name in ["model", "mode", "base_url", "api_key", "temperature", "context_window_size", "max_turns", "system_prompt", "provider"]:
            value = getattr(self.config.agent, field_name, "")
            if field_name == "api_key":
                value = self._mask_secret(str(value))
            table.add_row("agent", field_name, str(value))

        table.add_row("security", "mode", self.config.security.mode)
        table.add_row("security", "sandbox", str(self.config.security.sandbox))
        table.add_row("database", "path", self.config.database.path)
        table.add_row("logging", "level", self.config.logging.level)

        for name, prov in self.config.providers.items():
            table.add_row("provider", name, f"{prov.base_url}")

        for name, srv in getattr(self.config, 'mcp_servers', {}).items():
            table.add_row("mcp", name, f"{srv.command} {srv.transport}")

        self.console.print(table)

    def _search(self, args: str) -> None:
        """Search across sessions and memory."""
        if not args.strip():
            self.console.print("[dim]Usage: /search <query>[/]")
            return

        query = args.strip()

        # Search memory
        if self.db:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, self._search_memory(query)).result()
            else:
                asyncio.run(self._search_memory(query))
        else:
            self.console.print("[dim]No database available.[/]")

    async def _search_memory(self, query: str) -> None:
        """Search memory and display results."""
        from rich.table import Table

        records = await self.db.search_memory(query)
        if not records:
            self.console.print("[dim]No memories found.[/]")
            return

        table = Table(title=f"Memory Search: {query}")
        table.add_column("Content", style="cyan", max_width=50)
        table.add_column("Source", style="dim", max_width=15)
        table.add_column("Created", style="dim")

        for r in records[:10]:
            content = (r.get("content") or "")[:50]
            source = (r.get("source") or "")[:15]
            created = (r.get("created_at") or "")[:19]
            table.add_row(content, source, created)

        self.console.print(table)
        shown = min(len(records), 10)
        total = len(records)
        if total > 10:
            self.console.print(f"\n[dim]Showing {shown} of {total} results[/]")
        else:
            self.console.print(f"\n[dim]{total} results[/]")

    def _undo(self, _args: str) -> None:
        """Remove last user+assistant message pair."""
        if not self.messages:
            self.console.print("[dim]Nothing to undo.[/]")
            return

        # Don't undo a lone user message (no exchange to undo)
        if len(self.messages) == 1 and self.messages[0].role == "user":
            self.console.print("[dim]Nothing to undo — no reply yet.[/]")
            return

        # Remove last assistant message if present
        if self.messages[-1].role == "assistant":
            self.messages.pop()

        # Remove last user message if present
        if self.messages and self.messages[-1].role == "user":
            removed_user = self.messages.pop()
            self.console.print(f"[dim]Undid: {removed_user.content[:60]}[/]")
        elif not self.messages:
            self.console.print("[dim]Undid last message.[/]")
        else:
            self.console.print("[dim]Undid last assistant message.[/]")

        # Also remove from DB
        if self.db and self.session:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, self._undo_db()).result()
            else:
                asyncio.run(self._undo_db())

    async def _undo_db(self):
        """Remove last 2 messages from DB."""
        messages = await self.db.get_messages(self.session.id)
        if messages:
            to_delete = messages[-2:] if len(messages) >= 2 else messages[-1:]
            await self.db.delete_messages_by_ids([m.id for m in to_delete])

    def _retry(self, _args: str) -> None:
        """Remove last assistant message so it can be re-generated."""
        if not self.messages:
            self.console.print("[dim]Nothing to retry.[/]")
            return

        if self.messages[-1].role == "assistant":
            removed = self.messages.pop()
            self.console.print(f"[dim]Removed: {removed.content[:60]}...[/]")
            self.console.print("[dim]Re-submit your last message or the engine will retry.[/]")
        else:
            self.console.print("[dim]Last message is from user — just press Enter to retry.[/]")

        # Also remove from DB
        if self.db and self.session:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, self._retry_db()).result()
            else:
                asyncio.run(self._retry_db())

    async def _retry_db(self):
        """Remove last assistant message from DB."""
        messages = await self.db.get_messages(self.session.id)
        if messages and messages[-1].role == "assistant":
            await self.db.delete_messages_by_ids([messages[-1].id])

    def _resume(self, args: str) -> None:
        """Resume a previous session. No args = menu, number = pick by index, ID = direct."""
        target = args.strip()
        if not self.db:
            self.console.print("[dim]No database available.[/]")
            return

        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        def _run(coro):
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, coro).result()
            else:
                asyncio.run(coro)

        if target:
            if target.isdigit():
                _run(self._resume_by_number(int(target)))
            else:
                _run(self._resume_session(target))
        else:
            _run(self._resume_picker())

    async def _resume_by_number(self, n: int) -> None:
        """Resume session by list index (1-based)."""
        sessions = await self.db.list_sessions(limit=10)
        if 1 <= n <= len(sessions):
            await self._resume_session(sessions[n - 1].id)
        else:
            self.console.print(f"[red]Invalid number. There are {len(sessions)} sessions.[/]")

    async def _resume_picker(self) -> None:
        """Show session menu with interactive picker."""
        sessions = await self.db.list_sessions(limit=10)
        if not sessions:
            self.console.print("[dim]No sessions to resume.[/]")
            return

        # Build labels
        labels: list[str] = []
        for i, s in enumerate(sessions, 1):
            title = getattr(s, "title", "") or "(untitled)"
            time_str = s.created_at[:16].replace("T", " ")
            msg_count = len(await self.db.get_messages(s.id))
            labels.append(f"{i}. {title[:40]}  ({msg_count} msgs, {time_str})")

        idx = await _interactive_pick(labels, title="Sessions")
        if idx is not None:
            await self._resume_session(sessions[idx].id)

    async def _resume_session(self, session_id: str) -> bool:
        """Load a session and its messages into the current conversation."""
        session = await self.db.get_session(session_id)
        if session is None:
            self.console.print(f"[red]Session not found: {session_id}[/]")
            return False

        messages = await self.db.get_messages(session_id)
        if not messages:
            self.console.print("[dim]Session has no messages.[/]")
            return False

        self.messages.clear()
        for msg in messages:
            self.messages.append(Message(
                role=msg.role,
                content=msg.content,
                reasoning_content=msg.reasoning_content or None,
            ))

        self.session = session
        self.console.print(f"[green]Resumed session {session_id[:12]}... ({len(messages)} messages)[/]")
        return True

    def _clear(self, _args: str) -> None:
        self.messages.clear()
        self.console.print("[dim]Conversation cleared (in-memory only).[/]")

    def _mode_cmd(self, args: str) -> None:
        if not args:
            self.console.print(f"Current mode: [bold]{self.mode.value}[/]")
            return
        target = args.strip().lower()
        try:
            self.mode.mode = AgentMode(target)
        except ValueError:
            valid = ", ".join(m.value for m in AgentMode)
            self.console.print(f"[red]Invalid mode '{target}'. Choose from: {valid}[/]")
            return
        self.console.print(f"Mode switched to [bold]{self.mode.value}[/]")

    def _history(self, args: str) -> None:
        n = 10
        if args.strip():
            try:
                n = int(args.strip())
            except ValueError:
                self.console.print("[red]Usage: /history [N][/]")
                return
        if not self.messages:
            self.console.print("[dim]No messages yet.[/]")
            return
        tail = self.messages[-n:]
        for msg in tail:
            role_color = "blue" if msg.role == "user" else "green"
            content = msg.content
            if len(content) > 200:
                content = content[:200] + "..."
            self.console.print(f"  [{role_color}]{msg.role}:[/] {content}")

