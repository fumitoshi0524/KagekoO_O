"""Textual TUI for Kageko agent."""

from __future__ import annotations

import io
from typing import Any

from rich.console import Console
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Static, Header, RichLog
from textual.binding import Binding
from textual.reactive import reactive


class KagekoTUI(App):
    """Kageko agent TUI built with Textual."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #chat-log {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
        overflow-y: scroll;
    }

    #status-bar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    #input-area {
        height: 3;
        dock: bottom;
    }

    #user-input {
        width: 1fr;
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("up", "history_prev", "Previous input", show=False),
        Binding("down", "history_next", "Next input", show=False),
    ]

    status_text = reactive("Ready")

    def __init__(
        self,
        engine: Any = None,
        mode: Any = None,
        db: Any = None,
        session: Any = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.engine = engine
        self.mode = mode
        self.db = db
        self.session = session
        from kageko.types import Message
        self._messages: list[Message] = []
        self._input_history: list[str] = []
        self._history_index: int = -1

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self.status_text, id="status-bar")
        yield RichLog(id="chat-log", markup=True, wrap=True)
        with Horizontal(id="input-area"):
            yield Input(placeholder="Type your message...", id="user-input")

    def on_mount(self) -> None:
        self.query_one("#user-input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return

        event.input.clear()
        chat_log = self.query_one("#chat-log", RichLog)

        # Store in input history
        self._input_history.append(user_text)
        self._history_index = -1

        # Handle slash commands
        if user_text.startswith("/"):
            self._handle_slash_command(user_text, chat_log)
            return

        chat_log.write(f"[bold blue]You:[/] {user_text}")
        from kageko.types import Message
        self._messages.append(Message(role="user", content=user_text))
        self.status_text = "Thinking..."

        self.run_worker(self._process_message(chat_log))

    def _handle_slash_command(self, text: str, chat_log: RichLog) -> None:
        """Handle a slash command using SlashCommands with captured output."""
        from kageko.cli_commands import ModeRef, SlashCommands
        from kageko.types import AgentMode

        # Build a ModeRef if self.mode is an AgentMode
        if isinstance(self.mode, AgentMode):
            mode_ref = ModeRef(self.mode)
        elif isinstance(self.mode, ModeRef):
            mode_ref = self.mode
        else:
            mode_ref = ModeRef(AgentMode.tool_use)

        # Capture console output to a string
        buf = io.StringIO()
        capture_console = Console(file=buf, force_terminal=True, width=80)
        sc = SlashCommands(
            capture_console,
            self._messages,
            mode_ref,
            db=self.db,
            session=self.session,
        )

        # Handle /clear specially to also clear the TUI chat log
        if text.strip().lower() == "/clear":
            chat_log.clear()
            self._messages.clear()
            chat_log.write("[dim]Conversation cleared.[/]")
            return

        sc.handle(text)
        output = buf.getvalue().strip()
        if output:
            chat_log.write(output)

        # Sync mode back if it changed
        self.mode = mode_ref.mode

    async def _process_message(self, chat_log: RichLog) -> None:
        if not self.engine:
            chat_log.write("[dim]No engine configured[/]")
            self.status_text = "Ready"
            return

        from kageko.agent.ttsr import Correction
        from kageko.types import Message

        # Persist user message to DB if available
        if self.db and self.session:
            user_msg = self._messages[-1] if self._messages else None
            if user_msg and user_msg.role == "user":
                await self.db.append_message(self.session.id, role="user", content=user_msg.content)

        assistant_text = ""
        try:
            chat_log.write("[bold green]Kageko:[/] ", end="")
            async for tok in self.engine.run_stream(self._messages, mode=self.mode):
                if isinstance(tok, Correction):
                    chat_log.write(f"\n[bold red][TTSR][/]: {tok.message}")
                    break
                if hasattr(tok, "text") and tok.text:
                    chat_log.write(tok.text, end="")
                    assistant_text += tok.text
            chat_log.write("")
        except Exception as e:
            chat_log.write(f"\n[red]Error: {e}[/]")

        self._messages.append(Message(role="assistant", content=assistant_text or "(streamed)"))

        # Persist assistant message to DB if available
        if self.db and self.session:
            await self.db.append_message(self.session.id, role="assistant", content=assistant_text or "(streamed)")

        self.status_text = "Ready"

    def watch_status_text(self, new_value: str) -> None:
        try:
            self.query_one("#status-bar", Static).update(new_value)
        except Exception:
            pass

    def action_clear(self) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
        self._messages.clear()

    def action_history_prev(self) -> None:
        """Navigate to the previous input in history."""
        if not self._input_history:
            return
        if self._history_index <= 0:
            self._history_index = 0
        else:
            self._history_index -= 1
        input_widget = self.query_one("#user-input", Input)
        input_widget.value = self._input_history[self._history_index]

    def action_history_next(self) -> None:
        """Navigate to the next input in history."""
        if self._history_index < 0:
            return
        if self._history_index >= len(self._input_history) - 1:
            self._history_index = -1
            input_widget = self.query_one("#user-input", Input)
            input_widget.value = ""
        else:
            self._history_index += 1
            input_widget = self.query_one("#user-input", Input)
            input_widget.value = self._input_history[self._history_index]
