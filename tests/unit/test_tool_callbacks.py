"""Tests for tool execution callbacks in AgentEngine."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from kageko.agent.loop import AgentEngine
from kageko.agent.permissions import Decision, PermissionPipeline
from kageko.types import ToolCall


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    return llm


@pytest.fixture
def mock_registry():
    reg = MagicMock()
    reg.schemas.return_value = []
    reg.execute = AsyncMock(return_value="tool result")
    return reg


@pytest.fixture
def mock_permissions():
    perm = MagicMock(spec=PermissionPipeline)
    perm.check = AsyncMock(return_value=Decision.ALLOW)
    return perm


def test_engine_accepts_callbacks(mock_llm, mock_registry, mock_permissions):
    """AgentEngine should store on_tool_start and on_tool_end callbacks."""
    start_cb = AsyncMock()
    end_cb = AsyncMock()
    engine = AgentEngine(
        llm=mock_llm,
        tool_registry=mock_registry,
        permissions=mock_permissions,
        on_tool_start=start_cb,
        on_tool_end=end_cb,
    )
    assert engine.on_tool_start is start_cb
    assert engine.on_tool_end is end_cb


def test_engine_defaults_to_no_callbacks(mock_llm, mock_registry, mock_permissions):
    """AgentEngine should work without callbacks (backward compat)."""
    engine = AgentEngine(
        llm=mock_llm,
        tool_registry=mock_registry,
        permissions=mock_permissions,
    )
    assert engine.on_tool_start is None
    assert engine.on_tool_end is None


@pytest.mark.asyncio
async def test_callbacks_called_during_execution(mock_llm, mock_registry, mock_permissions):
    """Callbacks should fire when tool calls are executed."""
    start_cb = AsyncMock()
    end_cb = AsyncMock()
    engine = AgentEngine(
        llm=mock_llm,
        tool_registry=mock_registry,
        permissions=mock_permissions,
        on_tool_start=start_cb,
        on_tool_end=end_cb,
    )
    tool_calls = [ToolCall(id="1", name="echo", args={"text": "hi"})]
    await engine._execute_tool_calls(tool_calls)

    start_cb.assert_called_once_with("echo", {"text": "hi"})
    end_cb.assert_called_once_with("echo", "tool result", False)


@pytest.mark.asyncio
async def test_end_callback_called_on_error(mock_llm, mock_registry, mock_permissions):
    """on_tool_end should be called with is_error=True when tool raises."""
    mock_registry.execute = AsyncMock(side_effect=RuntimeError("boom"))
    end_cb = AsyncMock()
    engine = AgentEngine(
        llm=mock_llm,
        tool_registry=mock_registry,
        permissions=mock_permissions,
        on_tool_end=end_cb,
    )
    tool_calls = [ToolCall(id="1", name="bad_tool", args={})]
    await engine._execute_tool_calls(tool_calls)

    end_cb.assert_called_once()
    call_args = end_cb.call_args[0]
    assert call_args[0] == "bad_tool"
    assert "boom" in call_args[1]
    assert call_args[2] is True  # is_error


@pytest.mark.asyncio
async def test_end_callback_called_on_deny(mock_llm, mock_registry, mock_permissions):
    """on_tool_end should be called when tool is denied by permissions."""
    mock_permissions.check = AsyncMock(return_value=Decision.DENY)
    end_cb = AsyncMock()
    engine = AgentEngine(
        llm=mock_llm,
        tool_registry=mock_registry,
        permissions=mock_permissions,
        on_tool_end=end_cb,
    )
    tool_calls = [ToolCall(id="1", name="dangerous", args={})]
    await engine._execute_tool_calls(tool_calls)

    end_cb.assert_called_once()
    call_args = end_cb.call_args[0]
    assert call_args[2] is True  # is_error
