import pytest
from unittest.mock import MagicMock

from kageko.agent.context import ContextCompressor, ContextBudget
from kageko.learning.memory import MemoryManager
from kageko.types import Message, ToolCall


def _make_compressor(max_tokens=8000, head_count=2, tail_count=2):
    memory = MagicMock(spec=MemoryManager)
    memory.summarize_tool_result = MagicMock(
        side_effect=lambda name, result: f"[{name}] summarized"
    )
    llm = MagicMock()
    budget = ContextBudget(max_tokens=max_tokens, head_count=head_count, tail_count=tail_count)
    return ContextCompressor(memory=memory, llm=llm, budget=budget)


def test_compress_short_messages():
    messages = [
        Message(role="user", content="hi"),
        Message(role="assistant", content="hello"),
    ]
    compressor = _make_compressor(max_tokens=1000)
    result = compressor.compress(messages, current_tokens=50)
    assert result == messages


def test_compress_estimates_tokens():
    compressor = _make_compressor(max_tokens=100)
    long_msg = Message(role="user", content="x" * 400)
    tokens = compressor.estimate_tokens([long_msg])
    assert tokens >= 90


def test_compress_preserves_head_and_tail():
    messages = [
        Message(role="system", content="system prompt"),
        Message(role="user", content="a" * 1000),
        Message(role="assistant", content="b" * 1000),
        Message(role="user", content="c" * 1000),
        Message(role="assistant", content="final answer"),
    ]
    compressor = _make_compressor(max_tokens=100, head_count=1, tail_count=1)
    tokens = compressor.estimate_tokens(messages)
    result = compressor.compress(messages, current_tokens=tokens)
    assert result[0].role == "system"
    assert result[-1].content == "final answer"
    assert len(result) < len(messages) + 1


def test_estimate_tokens_includes_tool_calls():
    """Message with tool_calls should have higher token estimate than content alone."""
    plain_msg = Message(role="assistant", content="hello")
    tool_msg = Message(
        role="assistant",
        content="hello",
        tool_calls=[ToolCall(id="t1", name="echo", args={"text": "hello"})],
    )
    compressor = _make_compressor(max_tokens=10000)
    plain_tokens = compressor.estimate_tokens([plain_msg])
    tool_tokens = compressor.estimate_tokens([tool_msg])
    assert tool_tokens > plain_tokens


@pytest.mark.asyncio
async def test_compression_triggers_in_loop():
    """AgentEngine with tiny context_window_size should trigger compression on many messages."""
    from unittest.mock import AsyncMock
    from kageko.agent.loop import AgentEngine
    from kageko.agent.permissions import Decision, PermissionPipeline, SecurityMode
    from kageko.llm import LLMAdapter, LLMResponse
    from kageko.tools.registry import ToolRegistry, Tool
    from kageko.types import AgentMode

    registry = ToolRegistry()

    async def echo_handler(args):
        return "echo: " + args.get("text", "")

    registry.register(Tool(
        name="echo",
        description="Echo",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        handler=echo_handler,
        category="system",
    ))

    llm = AsyncMock(spec=LLMAdapter)
    # First call returns tool calls, second returns final answer
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[ToolCall(id="c1", name="echo", args={"text": "hi"})], tokens_used=20),
        LLMResponse(content="", tool_calls=[ToolCall(id="c2", name="echo", args={"text": "hi"})], tokens_used=20),
        LLMResponse(content="", tool_calls=[ToolCall(id="c3", name="echo", args={"text": "hi"})], tokens_used=20),
        LLMResponse(content="done", tool_calls=[], tokens_used=20),
    ])

    async def always_allow(tc):
        return Decision.ALLOW

    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE, prompt_fn=always_allow)
    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=10,
        context_window_size=50,  # Very tiny to force compression
    )

    result = await engine.run("echo hi", mode=AgentMode.TOOL_USE)
    assert result.answer == "done"
    assert result.turn_count == 4


def test_compression_preserves_system_prompt():
    """System prompt must survive compression and always be in head position."""
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="a" * 500),
        Message(role="assistant", content="b" * 500),
        Message(role="user", content="c" * 500),
        Message(role="assistant", content="d" * 500),
        Message(role="user", content="e" * 500),
        Message(role="assistant", content="last answer"),
    ]
    compressor = _make_compressor(max_tokens=50, head_count=1, tail_count=1)
    tokens = compressor.estimate_tokens(messages)
    result = compressor.compress(messages, current_tokens=tokens)
    # System prompt must be first
    assert result[0].role == "system"
    assert result[0].content == "You are a helpful assistant."
    # Last message preserved
    assert result[-1].content == "last answer"
    # Result is compressed
    assert len(result) < len(messages) + 1
