"""Tests for session resume, undo, and retry."""
from __future__ import annotations

import pytest
from rich.console import Console

from kageko.cli_commands import SlashCommands, ModeRef
from kageko.types import AgentMode, Message


@pytest.fixture
def console():
    from io import StringIO
    return Console(file=StringIO(), width=80, force_terminal=True)


def _make_sc(console):
    messages = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there!"),
        Message(role="user", content="How are you?"),
        Message(role="assistant", content="I'm doing well!"),
    ]
    mode = ModeRef(AgentMode.TOOL_USE)
    return SlashCommands(console, messages, mode), messages


def test_undo_removes_last_pair(console):
    sc, messages = _make_sc(console)
    assert len(messages) == 4
    result = sc.handle("/undo")
    assert result is True
    assert len(messages) == 2
    assert messages[-1].role == "assistant"
    assert messages[-1].content == "Hi there!"


def test_undo_nothing(console):
    sc = SlashCommands(console, [], ModeRef(AgentMode.TOOL_USE))
    result = sc.handle("/undo")
    assert result is True


def test_undo_single_message(console):
    messages = [Message(role="user", content="Hello")]
    sc = SlashCommands(console, messages, ModeRef(AgentMode.TOOL_USE))
    sc.handle("/undo")
    # Single message is below the threshold (< 2), nothing removed
    assert len(messages) == 1


def test_retry_removes_last_assistant(console):
    sc, messages = _make_sc(console)
    assert messages[-1].role == "assistant"
    sc.handle("/retry")
    assert len(messages) == 3
    assert messages[-1].role == "user"


def test_retry_no_assistant_message(console):
    messages = [Message(role="user", content="Hello")]
    sc = SlashCommands(console, messages, ModeRef(AgentMode.TOOL_USE))
    sc.handle("/retry")
    # Should not remove user message
    assert len(messages) == 1


def test_resume_lists_when_no_args(console):
    sc = SlashCommands(console, [], ModeRef(AgentMode.TOOL_USE))
    result = sc.handle("/resume")
    assert result is True
