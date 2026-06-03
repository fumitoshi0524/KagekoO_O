"""prompt_toolkit-based REPL with persistent history and tab completion."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

# Default slash command descriptions for completion metadata.
_SLASH_DESCRIPTIONS: dict[str, str] = {
    "/help": "Show available commands",
    "/clear": "Clear conversation history",
    "/mode": "Show or switch agent mode",
    "/history": "Show recent messages",
    "/resume": "Show sessions and pick one to resume",
    "/tools": "List available tools",
    "/model": "Show or switch model",
    "/undo": "Undo last exchange",
    "/retry": "Retry last assistant reply",
    "/config": "Show or edit configuration",
    "/search": "Search memory and sessions",
    "/memory": "Show recent memory entries (FTS5 recall)",
    "/skills-list": "List all extracted skills (active/stale/archived)",
    "/tools-generated": "List LLM-generated tools from QAOA patterns",
    "/evolution-stats": "Overview: memory / skills / tools / trajectories / curator",
    "/qaoa-generate": "Manually trigger tool generation from QAOA trajectories",
    "/qaoa-trajectories": "Show recent QAOA trajectory records",
    "/nudge-now": "Force immediate fact extraction (skip N-turn wait)",
    "/skill-extract": "Extract a reusable skill from recent conversation",
    "/quit": "Exit the chat session",
    "/exit": "Exit the chat session",
    "/q": "Exit the chat session",
}


class SlashCommandCompleter(Completer):
    """Tab-completes slash commands starting with ``/``."""

    def __init__(self, commands: Sequence[str]) -> None:
        self._commands = list(commands)

    def get_completions(self, document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor
        # Only complete when the user has typed something starting with /
        if not text.startswith("/"):
            return

        # Match against the first word (the command itself)
        parts = text.split()
        word = parts[0] if parts else text
        for cmd in self._commands:
            if cmd.startswith(word):
                yield Completion(
                    cmd,
                    start_position=-len(word),
                    display_meta=_SLASH_DESCRIPTIONS.get(cmd, ""),
                )


def make_keybindings() -> KeyBindings:
    """Create REPL key bindings.

    * Ctrl+C — clears input (if any), exits otherwise.
    * Ctrl+L — clears the screen.
    """
    kb = KeyBindings()

    @kb.add("c-c")
    def _ctrl_c(event):
        if event.current_buffer.text:
            event.current_buffer.reset()
        else:
            event.app.exit(exception=KeyboardInterrupt)

    @kb.add("c-l")
    def _ctrl_l(event):
        event.cli.output.erase_screen()
        event.cli.output.cursor_goto(0, 0)
        event.cli.renderer.reset()
        event.app.invalidate()

    return kb


REPL_STYLE = Style.from_dict(
    {
        "prompt": "cyan bold",
    }
)


def create_repl_session(
    history_file: str | Path | None = None,
    slash_commands: Sequence[str] | None = None,
    output: object | None = None,
) -> PromptSession[str]:
    """Build and return a :class:`PromptSession` for the interactive REPL.

    Parameters
    ----------
    history_file:
        Path to the persistent history file.  Defaults to ``~/.kageko/history``.
    slash_commands:
        List of slash command strings (e.g. ``["/help", "/clear"]``) used for
        tab completion.
    output:
        Optional prompt_toolkit output instance (use ``DummyOutput`` in tests).
    """
    if history_file is None:
        history_file = Path.home() / ".kageko" / "history"

    history_path = Path(history_file)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    completer = SlashCommandCompleter(slash_commands or [])
    kb = make_keybindings()

    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
        completer=completer,
        auto_suggest=AutoSuggestFromHistory(),
        key_bindings=kb,
        style=REPL_STYLE,
        multiline=False,
        enable_open_in_editor=True,
        output=output,
    )
    return session
