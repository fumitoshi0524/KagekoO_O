"""Textual TUI for Kageko agent."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Static, Header, RichLog
from textual.binding import Binding
from textual.reactive import reactive

from typing import Any


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
    ]

    status_text = reactive("Ready")

    def __init__(self, engine: Any = None, mode: Any = None, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.mode = mode
        self._history: list[dict[str, str]] = []

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

        chat_log.write(f"[bold blue]You:[/] {user_text}")
        self._history.append({"role": "user", "content": user_text})
        self.status_text = "Thinking..."

        self.run_worker(self._process_message(user_text, chat_log))

    async def _process_message(self, text: str, chat_log: RichLog) -> None:
        if not self.engine:
            chat_log.write("[dim]No engine configured[/]")
            self.status_text = "Ready"
            return

        from kageko.agent.ttsr import Correction
        try:
            chat_log.write("[bold green]Kageko:[/] ", end="")
            async for tok in self.engine.run_stream(text, mode=self.mode):
                if isinstance(tok, Correction):
                    chat_log.write(f"\n[bold red][TTSR][/]: {tok.message}")
                    break
                if hasattr(tok, "text") and tok.text:
                    chat_log.write(tok.text, end="")
            chat_log.write("")
        except Exception as e:
            chat_log.write(f"\n[red]Error: {e}[/]")

        self._history.append({"role": "assistant", "content": "(streamed)"})
        self.status_text = "Ready"

    def watch_status_text(self, new_value: str) -> None:
        try:
            self.query_one("#status-bar", Static).update(new_value)
        except Exception:
            pass

    def action_clear(self) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
        self._history.clear()
