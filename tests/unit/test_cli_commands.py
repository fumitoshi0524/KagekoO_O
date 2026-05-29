"""Tests for CLI slash commands."""
from __future__ import annotations

import pytest
from rich.console import Console

from kageko.cli_commands import ModeRef, SlashCommands
from kageko.types import AgentMode, Message


@pytest.fixture
def console():
    return Console()


def test_slash_help(console):
    messages: list[Message] = []
    mode = ModeRef(AgentMode.TOOL_USE)
    sc = SlashCommands(console, messages, mode)
    assert sc.handle("/help") is True


def test_slash_clear(console):
    messages = [Message(role="user", content="hi")]
    mode = ModeRef(AgentMode.TOOL_USE)
    sc = SlashCommands(console, messages, mode)
    sc.handle("/clear")
    assert len(messages) == 0


def test_non_slash_returns_false(console):
    sc = SlashCommands(console, [], ModeRef(AgentMode.TOOL_USE))
    assert sc.handle("hello") is False


def test_unknown_slash_returns_true(console):
    sc = SlashCommands(console, [], ModeRef(AgentMode.TOOL_USE))
    assert sc.handle("/nonexistent") is True


def test_slash_mode_shows_current(console):
    sc = SlashCommands(console, [], ModeRef(AgentMode.TOOL_USE))
    assert sc.handle("/mode") is True


def test_slash_mode_switch(console):
    mode = ModeRef(AgentMode.TOOL_USE)
    sc = SlashCommands(console, [], mode)
    sc.handle("/mode qaoa")
    assert mode.value == "qaoa"


def test_slash_history(console):
    messages = [
        Message(role="user", content="hello"),
        Message(role="assistant", content="hi there"),
    ]
    sc = SlashCommands(console, messages, ModeRef(AgentMode.TOOL_USE))
    assert sc.handle("/history") is True


def test_slash_history_with_n(console):
    messages = [
        Message(role="user", content="a"),
        Message(role="assistant", content="b"),
        Message(role="user", content="c"),
    ]
    sc = SlashCommands(console, messages, ModeRef(AgentMode.TOOL_USE))
    assert sc.handle("/history 1") is True


def test_slash_session_removed(console):
    sc = SlashCommands(console, [], ModeRef(AgentMode.TOOL_USE))
    # /session and /sessions removed — merged into /resume
    assert sc.handle("/session") is True  # treated as unknown command


def test_slash_resume_no_db(console):
    sc = SlashCommands(console, [], ModeRef(AgentMode.TOOL_USE))
    assert sc.handle("/resume") is True


def test_slash_clear_then_empty(console):
    messages: list[Message] = []
    sc = SlashCommands(console, messages, ModeRef(AgentMode.TOOL_USE))
    sc.handle("/clear")
    assert len(messages) == 0


def test_slash_help_case_insensitive(console):
    sc = SlashCommands(console, [], ModeRef(AgentMode.TOOL_USE))
    assert sc.handle("/HELP") is True
