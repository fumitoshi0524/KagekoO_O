"""Streaming output handler — spinner + token-by-token output."""
from __future__ import annotations

from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live


class StreamHandler:
    """Manages streaming LLM output with Rich rendering.

    While tokens arrive: prints them raw for immediate feedback.
    On finish(): prints newline after stream completes.
    """

    def __init__(self, console: Console) -> None:
        self.console = console
        self._live: Live | None = None

    def start_spinner(self, message: str = "Thinking...") -> None:
        spinner = Spinner("dots", text=message)
        self._live = Live(spinner, console=self.console, refresh_per_second=10)
        self._live.start()

    def stop_spinner(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None

    def on_token(self, text: str) -> None:
        self.stop_spinner()
        self.console.print(text, end="", highlight=False)

    def finish(self) -> None:
        self.stop_spinner()
        self.console.print()
