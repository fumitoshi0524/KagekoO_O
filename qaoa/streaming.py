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


_RISK_COLORS = {"read": "green", "write": "yellow", "destructive": "red"}
_RISK_ICONS = {"read": "📖", "write": "✏️", "destructive": "⚠️"}


@dataclass(slots=True, kw_only=True)
class ConsoleStreamRenderer:
    """Prints StreamEvents to console with agent-activity-aware formatting.

    Shows tool calls with risk-colored indicators, thinking in dim text,
    and structured tool results with length/line summaries.
    """

    _console: object = None
    _tool_count: int = 0
    _thinking_active: bool = False
    _current_tool_name: str = ""
    _current_tool_risk: str = "read"
    _current_tool_args: list[str] = field(default_factory=list)
    _first_text: bool = True
    _text_started: bool = False

    def __post_init__(self):
        from rich.console import Console
        self._console = Console()

    def on_event(self, event: StreamEvent) -> None:
        if event.type == StreamEventType.THINKING_START:
            self._thinking_active = True

        elif event.type == StreamEventType.THINKING_DELTA and event.text:
            if self._text_started:
                self._console.print()
                self._text_started = False
            if self._thinking_active:
                self._console.print(f"  [dim]💭 {event.text}[/dim]", end="")

        elif event.type == StreamEventType.THINKING_DONE:
            self._thinking_active = False
            if self._first_text:
                self._console.print()

        elif event.type == StreamEventType.TOOL_CALL_START:
            self._tool_count += 1
            self._current_tool_name = event.tool_name or "tool"
            self._current_tool_risk = "read"
            self._current_tool_args = []
            if self._text_started:
                self._console.print()
                self._text_started = False
            color = _RISK_COLORS.get(self._current_tool_risk, "white")
            icon = _RISK_ICONS.get(self._current_tool_risk, "🔧")
            self._console.print(f"  [{color}]{icon} {self._current_tool_name}[/{color}]")

        elif event.type == StreamEventType.TOOL_CALL_ARGS:
            if event.text:
                self._current_tool_args.append(event.text)
            if event.tool_name:
                self._current_tool_name = event.tool_name

        elif event.type == StreamEventType.TOOL_CALL_END:
            if event.tool_input:
                self._current_tool_args = [event.tool_input]
            # Show key arguments
            if self._current_tool_args:
                arg_text = " ".join(self._current_tool_args)
                for line in arg_text.split("\n")[:3]:
                    truncated = line[:100] + "..." if len(line) > 100 else line
                    if truncated.strip():
                        self._console.print(f"     [dim]{truncated}[/dim]")

        elif event.type == StreamEventType.TOOL_RESULT:
            tool_name = event.tool_name or "tool"
            output = event.tool_output or ""
            lines = output.count("\n") + 1 if output else 0
            size = len(output)
            if size > 200:
                preview = output[:200].replace("\n", " ").strip() + "..."
            elif size > 0:
                preview = output.replace("\n", " ").strip()
            else:
                preview = "<empty>"
            summary = f"{size}B" if size < 1024 else f"{size / 1024:.1f}KB"
            if lines > 1:
                summary += f", {lines} lines"
            self._console.print(f"     [green]✓ {summary}[/green] [dim]{preview[:80]}[/dim]")

        elif event.type == StreamEventType.ERROR:
            if self._text_started:
                self._console.print()
                self._text_started = False
            self._console.print(f"  [red]✗ {event.text}[/red]")

        elif event.type == StreamEventType.TEXT_DELTA and event.text:
            if self._first_text:
                self._first_text = False
                self._text_started = True
            self._console.print(event.text, end="")

        elif event.type == StreamEventType.DONE:
            if self._text_started:
                self._console.print()
            if self._tool_count > 0:
                self._console.print(f"  [dim]— {self._tool_count} tool{'s' if self._tool_count > 1 else ''} used[/dim]")
            else:
                self._console.print()

    def on_done(self) -> None:
        pass
