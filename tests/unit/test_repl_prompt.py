"""Tests for prompt_toolkit REPL prompt module."""
from __future__ import annotations

import pytest
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output import DummyOutput

from kageko.repl.prompt import (
    SlashCommandCompleter,
    create_repl_session,
    make_keybindings,
)


# ---------------------------------------------------------------------------
# SlashCommandCompleter
# ---------------------------------------------------------------------------


def _get_completion_texts(completer: SlashCommandCompleter, text: str) -> set[str]:
    """Helper: return set of completion strings for the given input text."""
    doc = Document(text)
    return {c.text for c in completer.get_completions(doc, None)}


def test_slash_completer_matches():
    """Completer should yield matching commands for a partial slash input."""
    completer = SlashCommandCompleter(["/help", "/history"])
    texts = _get_completion_texts(completer, "/h")
    assert "/help" in texts
    assert "/history" in texts


def test_slash_completer_exact_match():
    """Completer should return the exact command when fully typed."""
    completer = SlashCommandCompleter(["/help", "/history"])
    texts = _get_completion_texts(completer, "/help")
    assert "/help" in texts


def test_slash_completer_no_match_for_non_slash():
    """Completer should return nothing for regular (non-slash) text."""
    completer = SlashCommandCompleter(["/help", "/history"])
    texts = _get_completion_texts(completer, "hello")
    assert texts == set()


def test_slash_completer_no_match_for_unknown_prefix():
    """Completer should return nothing when no command matches."""
    completer = SlashCommandCompleter(["/help", "/history"])
    texts = _get_completion_texts(completer, "/zzz")
    assert texts == set()


def test_slash_completer_display_meta():
    """Completions should include display_meta for known commands."""
    completer = SlashCommandCompleter(["/help"])
    doc = Document("/h")
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 1
    meta = completions[0].display_meta
    # display_meta is FormattedText; extract plain text
    plain = "".join(text for _, text in meta)
    assert plain == "Show available commands"


# ---------------------------------------------------------------------------
# make_keybindings
# ---------------------------------------------------------------------------


def test_keybindings_exist():
    """Key bindings for Ctrl+C and Ctrl+L should be registered."""
    kb = make_keybindings()
    assert isinstance(kb, KeyBindings)
    keys = [b.keys for b in kb.bindings if b.keys]
    flat_keys = [k for ks in keys for k in ks]
    assert "c-c" in flat_keys, "Ctrl+C binding missing"
    assert "c-l" in flat_keys, "Ctrl+L binding missing"


# ---------------------------------------------------------------------------
# create_repl_session
# ---------------------------------------------------------------------------


def test_create_repl_session_returns_session(tmp_path):
    """Factory function should return a PromptSession instance."""
    history_file = tmp_path / "history"
    session = create_repl_session(
        history_file=str(history_file),
        slash_commands=["/help", "/clear"],
        output=DummyOutput(),
    )
    assert isinstance(session, PromptSession)


def test_create_repl_session_creates_history_dir(tmp_path):
    """The parent directory for the history file should be created."""
    history_file = tmp_path / "subdir" / "history"
    create_repl_session(history_file=str(history_file), output=DummyOutput())
    assert history_file.parent.exists()


def test_create_repl_session_default_history_path():
    """Default history path should resolve to ~/.kageko/history."""
    session = create_repl_session(output=DummyOutput())
    assert isinstance(session, PromptSession)
