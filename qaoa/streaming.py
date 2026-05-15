"""Streaming infrastructure for real-time LLM responses and tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterator, AsyncIterator, Protocol, runtime_checkable


class StreamEventType(StrEnum):
    TEXT_DELTA = "text_delta"
    TEXT_DONE = "text_done"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_ARGS = "tool_call_args"
    TOOL_CALL_END = "tool_call_end"
    TOOL_RESULT = "tool_result"
    THINKING_START = "thinking_start"
    THINKING_DELTA = "thinking_delta"
    THINKING_DONE = "thinking_done"
    ERROR = "error"
    DONE = "done"


@dataclass(slots=True, kw_only=True)
class StreamEvent:
    type: StreamEventType
    text: str | None = None
    tool_id: str | None = None
    tool_name: str | None = None
    tool_input: str | None = None
    tool_output: str | None = None
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class StreamConsumer(Protocol):
    """Something that accepts StreamEvents — console, file, callback, etc."""
    def on_event(self, event: StreamEvent) -> None: ...
    def on_done(self) -> None: ...


@dataclass(slots=True, kw_only=True)
class ConsoleStreamRenderer:
    """Prints StreamEvents directly to console — no Live display complexity."""

    _console: object = None
    _tool_lines: list = field(default_factory=list)
    _first_text: bool = True

    def __post_init__(self):
        from rich.console import Console
        self._console = Console()

    def on_event(self, event: StreamEvent) -> None:
        if event.type == StreamEventType.TEXT_DELTA and event.text:
            if self._first_text:
                self._first_text = False
            self._console.print(event.text, end="")

        elif event.type == StreamEventType.TOOL_RESULT:
            tool_name = event.tool_name or "tool"
            preview = (event.tool_output or "")[:100].replace("\n", " ")
            line = f"[dim]⚙ {tool_name}: {preview}{'...' if len(event.tool_output or '') > 100 else ''}[/dim]"
            self._tool_lines.append(line)
            self._console.print(f"\n  {line}")

        elif event.type == StreamEventType.ERROR:
            self._console.print(f"\n  [red]✗ {event.text}[/red]")

        elif event.type == StreamEventType.DONE:
            self._console.print()  # final newline

    def on_done(self) -> None:
        pass
