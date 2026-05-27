"""Tests for AgentEngine constructor and run loop."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kageko.agent.loop import AgentContext, AgentEngine
from kageko.config import AgentConfig
from kageko.types import AgentResult, Message, ToolCall, ToolResult


@pytest.fixture
def mock_llm():
    """Create a mock LLM adapter that returns no tool calls by default."""
    llm = MagicMock()
    llm.model = "test-model"
    llm.api_key = "test-key"
    llm.base_url = "https://api.example.com/v1"
    llm.chat = AsyncMock(return_value=MagicMock(
        content="Hello!",
        tool_calls=[],
        tokens_used=10,
        has_tool_calls=lambda: False,
    ))
    return llm


@pytest.fixture
def config():
    return AgentConfig(model="test-model", api_key="test-key")


class TestAgentEngineConstructor:
    def test_default_construction(self, config):
        engine = AgentEngine(config=config)
        assert engine.config is config
        assert engine.registry is not None
        assert engine.memory is None
        assert engine.compressor is None
        assert engine.guardrails is None

    def test_custom_registry(self, config):
        from kageko.tools.registry import ToolRegistry
        registry = ToolRegistry()
        engine = AgentEngine(config=config, registry=registry)
        assert engine.registry is registry

    def test_builtin_tools_registered(self, config):
        engine = AgentEngine(config=config)
        names = engine.registry.list_names()
        # Core builtin tools should be registered
        assert "file_read" in names
        assert "file_write" in names
        assert "bash" in names
        assert "echo" in names

    def test_with_memory(self, config):
        from kageko.learning.memory import MemoryManager
        db = MagicMock()
        memory = MemoryManager(db)
        engine = AgentEngine(config=config, memory=memory)
        assert engine.memory is memory

    def test_with_compressor(self, config):
        from kageko.agent.context import ContextCompressor, ContextBudget
        from kageko.learning.memory import MemoryManager
        db = MagicMock()
        memory = MemoryManager(db)
        compressor = ContextCompressor(memory=memory, llm=MagicMock(), budget=ContextBudget())
        engine = AgentEngine(config=config, memory=memory, compressor=compressor)
        assert engine.compressor is compressor

    def test_with_guardrails(self, config):
        from kageko.agent.guardrails import ToolGuardrail
        guardrails = ToolGuardrail()
        engine = AgentEngine(config=config, guardrails=guardrails)
        assert engine.guardrails is guardrails

    def test_with_all_dependencies(self, config):
        from kageko.tools.registry import ToolRegistry
        from kageko.learning.memory import MemoryManager
        from kageko.agent.context import ContextCompressor, ContextBudget
        from kageko.agent.guardrails import ToolGuardrail

        registry = ToolRegistry()
        db = MagicMock()
        memory = MemoryManager(db)
        compressor = ContextCompressor(memory=memory, llm=MagicMock(), budget=ContextBudget())
        guardrails = ToolGuardrail()

        engine = AgentEngine(
            config=config,
            registry=registry,
            memory=memory,
            compressor=compressor,
            guardrails=guardrails,
        )
        assert engine.registry is registry
        assert engine.memory is memory
        assert engine.compressor is compressor
        assert engine.guardrails is guardrails

    def test_legacy_construction(self):
        """Support the old direct-parameter constructor for backward compat."""
        llm = MagicMock()
        llm.model = "gpt-4"
        registry = MagicMock()
        engine = AgentEngine(llm=llm, tool_registry=registry)
        assert engine.llm is llm
        assert engine.registry is registry


class TestAgentEngineRun:
    @pytest.mark.asyncio
    async def test_run_returns_answer(self, config, mock_llm):
        engine = AgentEngine(config=config)
        engine.llm = mock_llm

        result = await engine.run("Hello")
        assert isinstance(result, AgentResult)
        assert result.answer == "Hello!"
        assert result.turn_count == 1

    @pytest.mark.asyncio
    async def test_run_with_tool_calls(self, config):
        from kageko.tools.registry import ToolRegistry, Tool

        registry = ToolRegistry()
        registry.register(Tool(
            name="echo",
            description="Echo text",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
            handler=AsyncMock(return_value="echoed"),
            category="test",
        ))

        # First call returns a tool call, second returns final answer
        llm = MagicMock()
        llm.model = "test"
        llm.api_key = "test"
        llm.base_url = "https://test.com/v1"
        llm.chat = AsyncMock(side_effect=[
            MagicMock(
                content="",
                tool_calls=[ToolCall(id="tc1", name="echo", args={"text": "hi"})],
                tokens_used=10,
                has_tool_calls=lambda: True,
            ),
            MagicMock(
                content="Done!",
                tool_calls=[],
                tokens_used=5,
                has_tool_calls=lambda: False,
            ),
        ])

        engine = AgentEngine(config=config, registry=registry)
        engine.llm = llm

        result = await engine.run("echo hi")
        assert result.answer == "Done!"
        assert result.turn_count == 2

    @pytest.mark.asyncio
    async def test_run_max_turns(self, config):
        llm = MagicMock()
        llm.model = "test"
        llm.api_key = "test"
        llm.base_url = "https://test.com/v1"
        # Always return a tool call to force max turns
        llm.chat = AsyncMock(return_value=MagicMock(
            content="",
            tool_calls=[ToolCall(id="tc1", name="echo", args={})],
            tokens_used=5,
            has_tool_calls=lambda: True,
        ))

        config.max_turns = 2
        engine = AgentEngine(config=config)
        engine.llm = llm

        result = await engine.run("loop forever")
        assert result.answer == "(max turns reached)"
        assert result.turn_count == 2


class TestAgentEngineGuardrails:
    @pytest.mark.asyncio
    async def test_guardrails_block(self, config):
        from kageko.agent.guardrails import ToolGuardrail, GuardrailConfig

        guard_config = GuardrailConfig(same_call_block=2)
        guardrails = ToolGuardrail(config=guard_config)

        llm = MagicMock()
        llm.model = "test"
        llm.api_key = "test"
        llm.base_url = "https://test.com/v1"
        # Return the same tool call twice - guardrail should block on second
        llm.chat = AsyncMock(side_effect=[
            MagicMock(
                content="",
                tool_calls=[ToolCall(id="tc1", name="echo", args={"text": "hi"})],
                tokens_used=5,
                has_tool_calls=lambda: True,
            ),
            MagicMock(
                content="",
                tool_calls=[ToolCall(id="tc2", name="echo", args={"text": "hi"})],
                tokens_used=5,
                has_tool_calls=lambda: True,
            ),
            MagicMock(
                content="Stopped due to guardrail",
                tool_calls=[],
                tokens_used=5,
                has_tool_calls=lambda: False,
            ),
        ])

        engine = AgentEngine(
            config=config,
            guardrails=guardrails,
        )
        engine.llm = llm
        # Override the builtin echo with a mock handler
        from kageko.tools.registry import Tool
        engine.registry.register(Tool(
            name="echo",
            description="Echo",
            parameters={},
            handler=AsyncMock(return_value="hi"),
            category="test",
        ), override=True)

        result = await engine.run("echo hi")
        # First tool call succeeds, second is blocked
        assert result.turn_count == 3


class TestAgentEngineMemory:
    @pytest.mark.asyncio
    async def test_memory_prefetch(self, config):
        from kageko.learning.memory import MemoryManager, MemoryEntry

        db = MagicMock()
        memory = MemoryManager(db)
        memory.prefetch = AsyncMock(return_value=[
            MemoryEntry(id="1", content="Previous context about coding"),
        ])
        memory.sync_turn = AsyncMock()

        llm = MagicMock()
        llm.model = "test"
        llm.api_key = "test"
        llm.base_url = "https://test.com/v1"
        llm.chat = AsyncMock(return_value=MagicMock(
            content="Answer with context",
            tool_calls=[],
            tokens_used=10,
            has_tool_calls=lambda: False,
        ))

        engine = AgentEngine(config=config, memory=memory)
        engine.llm = llm

        result = await engine.run("What did we discuss?")
        assert result.answer == "Answer with context"
        memory.prefetch.assert_called_once()
        memory.sync_turn.assert_called_once()


class TestAgentEngineCompression:
    @pytest.mark.asyncio
    async def test_compression_triggers_on_large_context(self, config):
        from kageko.agent.context import ContextCompressor, ContextBudget
        from kageko.learning.memory import MemoryManager

        db = MagicMock()
        memory = MemoryManager(db)
        budget = ContextBudget(max_tokens=100)
        compressor = ContextCompressor(memory=memory, llm=MagicMock(), budget=budget)

        # Make estimate_tokens return a large value
        compressor.estimate_tokens = MagicMock(return_value=90)  # > 100 * 0.8 = 80
        compressor.compress = MagicMock(return_value=[
            Message(role="user", content="compressed"),
        ])

        llm = MagicMock()
        llm.model = "test"
        llm.api_key = "test"
        llm.base_url = "https://test.com/v1"
        llm.chat = AsyncMock(return_value=MagicMock(
            content="Done",
            tool_calls=[],
            tokens_used=5,
            has_tool_calls=lambda: False,
        ))

        config.context_window_size = 100
        engine = AgentEngine(config=config, memory=memory, compressor=compressor)
        engine.llm = llm

        result = await engine.run("Tell me something")
        compressor.compress.assert_called()
