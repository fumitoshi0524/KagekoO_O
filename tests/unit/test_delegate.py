"""Tests for delegation system."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from kageko.agent.delegate import DelegationEngine, SubagentResult, make_delegate_handler
from kageko.types import AgentMode, Message


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.llm = MagicMock()
    engine.tool_registry = MagicMock()
    engine.tool_registry.list_names.return_value = []
    result = MagicMock()
    result.answer = "Task completed"
    result.turn_count = 2
    result.tokens_used = 100
    engine.run = AsyncMock(return_value=result)
    return engine


@pytest.fixture
def subagent_result():
    result = MagicMock()
    result.answer = "Task completed"
    result.turn_count = 2
    result.tokens_used = 100
    return result


def test_subagent_result():
    r = SubagentResult(task_id="abc123", answer="done")
    assert r.task_id == "abc123"
    assert r.is_error is False


def test_subagent_result_error():
    r = SubagentResult(task_id="", answer="failed", is_error=True)
    assert r.is_error is True


def test_delegation_engine_init(mock_engine):
    de = DelegationEngine(mock_engine)
    assert de.parent is mock_engine


@pytest.mark.asyncio
async def test_delegate_creates_result(mock_engine, subagent_result):
    with patch("kageko.agent.loop.AgentEngine") as mock_engine_cls:
        mock_sub_engine = MagicMock()
        mock_sub_engine.run = AsyncMock(return_value=subagent_result)
        mock_engine_cls.return_value = mock_sub_engine

        de = DelegationEngine(mock_engine)
        result = await de.delegate("test task")
        assert isinstance(result, SubagentResult)
        assert result.answer == "Task completed"
        assert result.is_error is False
        mock_engine_cls.assert_called_once()


@pytest.mark.asyncio
async def test_delegate_on_error(mock_engine):
    with patch("kageko.agent.loop.AgentEngine") as mock_engine_cls:
        mock_sub_engine = MagicMock()
        mock_sub_engine.run = AsyncMock(side_effect=RuntimeError("boom"))
        mock_engine_cls.return_value = mock_sub_engine

        de = DelegationEngine(mock_engine)
        result = await de.delegate("failing task")
        assert result.is_error is True
        assert "boom" in result.answer


@pytest.mark.asyncio
async def test_delegate_parallel(mock_engine, subagent_result):
    with patch("kageko.agent.loop.AgentEngine") as mock_engine_cls:
        mock_sub_engine = MagicMock()
        mock_sub_engine.run = AsyncMock(return_value=subagent_result)
        mock_engine_cls.return_value = mock_sub_engine

        de = DelegationEngine(mock_engine)
        results = await de.delegate_parallel(["task 1", "task 2"])
        assert len(results) == 2
        assert all(isinstance(r, SubagentResult) for r in results)


@pytest.mark.asyncio
async def test_make_delegate_handler(mock_engine, subagent_result):
    with patch("kageko.agent.loop.AgentEngine") as mock_engine_cls:
        mock_sub_engine = MagicMock()
        mock_sub_engine.run = AsyncMock(return_value=subagent_result)
        mock_engine_cls.return_value = mock_sub_engine

        handler = make_delegate_handler(mock_engine)
        assert callable(handler)
        result = await handler({"task": "do something"})
        assert "Task completed" in result


@pytest.mark.asyncio
async def test_delegate_handler_no_task(mock_engine):
    handler = make_delegate_handler(mock_engine)
    result = await handler({})
    assert "ERROR" in result
