"""Tests for enhanced slash commands (/tools, /model, /config, /help)."""
from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from kageko.cli_commands import SlashCommands, ModeRef
from kageko.types import AgentMode, Message


def _console():
    return Console(file=StringIO(), width=120, force_terminal=True)


def _mock_registry():
    reg = MagicMock()
    tool1 = MagicMock()
    tool1.name = "file_read"
    tool1.description = "Read a file"
    tool1.category = "file"
    tool1.parameters = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
    tool2 = MagicMock()
    tool2.name = "bash_run"
    tool2.description = "Run a bash command"
    tool2.category = "shell"
    tool2.parameters = {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
    reg.list.return_value = [tool1, tool2]
    return reg


def _mock_config():
    config = MagicMock()
    config.agent.model = "gpt-4o"
    config.agent.base_url = "https://api.openai.com/v1"
    config.agent.temperature = 0.7
    config.agent.mode = "tool-use"
    config.agent.context_window_size = 8000
    config.agent.max_turns = 20
    config.agent.provider = "openai"
    config.security.mode = "interactive"
    config.security.sandbox = False
    config.database.path = "~/.kageko/kageko.db"
    config.logging.level = "INFO"
    config.providers = {}
    config.mcp_servers = {}
    return config


def test_tools_command():
    c = _console()
    sc = SlashCommands(c, [], ModeRef(AgentMode.TOOL_USE), tool_registry=_mock_registry())
    result = sc.handle("/tools")
    assert result is True
    output = c.file.getvalue()  # type: ignore
    assert "file_read" in output
    assert "bash_run" in output


def test_tools_no_registry():
    c = _console()
    sc = SlashCommands(c, [], ModeRef(AgentMode.TOOL_USE))
    sc.handle("/tools")
    assert "No tool registry" in c.file.getvalue()  # type: ignore


def test_model_show():
    c = _console()
    config = _mock_config()
    sc = SlashCommands(c, [], ModeRef(AgentMode.TOOL_USE), config=config)
    sc.handle("/model")
    output = c.file.getvalue()  # type: ignore
    assert "gpt-4o" in output


def test_model_switch():
    c = _console()
    config = _mock_config()
    sc = SlashCommands(c, [], ModeRef(AgentMode.TOOL_USE), config=config)
    sc.handle("/model deepseek-chat")
    assert config.agent.model == "deepseek-chat"


def test_config_command():
    c = _console()
    config = _mock_config()
    sc = SlashCommands(c, [], ModeRef(AgentMode.TOOL_USE), config=config)
    result = sc.handle("/config")
    assert result is True
    output = c.file.getvalue()  # type: ignore
    assert "gpt-4o" in output


def test_help_categorized():
    c = _console()
    sc = SlashCommands(c, [], ModeRef(AgentMode.TOOL_USE))
    sc.handle("/help")
    output = c.file.getvalue()  # type: ignore
    assert "Session" in output
    assert "Tools & Models" in output
    assert "Info" in output


def test_help_specific_command():
    c = _console()
    sc = SlashCommands(c, [], ModeRef(AgentMode.TOOL_USE))
    sc.handle("/help tools")
    output = c.file.getvalue()  # type: ignore
    assert "tools" in output.lower()
