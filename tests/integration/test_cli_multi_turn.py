"""Integration tests for multi-turn conversation, tool use, and context compression."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from kageko.agent.loop import AgentEngine
from kageko.agent.permissions import PermissionPipeline, SecurityMode
from kageko.data.db import KagekoDB
from kageko.llm import LLMResponse
from kageko.tools.registry import ToolRegistry, Tool
from kageko.types import AgentMode, AgentResult, Message, StreamToken, ToolCall


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _echo_handler(args: dict) -> str:
    return f"echo: {args.get('text', '')}"


@pytest.fixture
async def db():
    """In-memory KagekoDB for testing."""
    d = KagekoDB(":memory:")
    await d.init()
    yield d
    await d.close()


@pytest.fixture
def engine():
    """AgentEngine with real registry, permissive permissions, and mock LLM."""
    llm = AsyncMock()
    registry = ToolRegistry()
    registry.register(Tool(
        name="echo",
        description="Echo text back",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        handler=_echo_handler,
        category="test",
    ))
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    return AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=10,
        system_prompt="You are a helpful assistant.",
        context_window_size=8000,
    ), llm


# ---------------------------------------------------------------------------
# Test: Multi-turn conversation with real DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_turn_accumulates_messages(db):
    """Two-turn conversation: verify messages accumulate across turns."""
    llm = AsyncMock()
    registry = ToolRegistry()
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=10,
    )

    session = await db.create_session("test", "chat_001")

    # Turn 1
    llm.chat = AsyncMock(return_value=LLMResponse(
        content="Hello! How can I help?", tool_calls=[], tokens_used=10,
    ))
    result1 = await engine.run("Hi there")
    assert result1.answer == "Hello! How can I help?"
    assert result1.turn_count == 1

    # Persist turn 1 to DB
    await db.append_messages_batch(session.id, [
        ("user", "Hi there"),
        ("assistant", result1.answer),
    ])

    # Turn 2 (continue with prior messages)
    llm.chat = AsyncMock(return_value=LLMResponse(
        content="Sure, I can help with that.", tool_calls=[], tokens_used=15,
    ))
    prior_messages = list(result1.messages)
    prior_messages.append(Message(role="user", content="Tell me about Python"))
    result2 = await engine.run(prior_messages)
    assert result2.answer == "Sure, I can help with that."
    assert result2.turn_count == 1

    # Persist turn 2 to DB
    await db.append_messages_batch(session.id, [
        ("user", "Tell me about Python"),
        ("assistant", result2.answer),
    ])

    # Verify DB has all 4 messages
    records = await db.get_messages(session.id)
    assert len(records) == 4
    assert records[0].role == "user" and records[0].content == "Hi there"
    assert records[1].role == "assistant" and records[1].content == "Hello! How can I help?"
    assert records[2].role == "user" and records[2].content == "Tell me about Python"
    assert records[3].role == "assistant" and records[3].content == "Sure, I can help with that."


# ---------------------------------------------------------------------------
# Test: Tool use with permission check and DB persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_use_with_db_persistence(engine, db):
    """Mock LLM returns a tool call, verify execution, permission check, and DB storage."""
    engine_inst, llm = engine

    call_count = 0

    async def mock_chat(messages, tools=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="tc1", name="echo", args={"text": "hello"})],
                tokens_used=5,
            )
        return LLMResponse(content="Done! Echoed hello.", tool_calls=[], tokens_used=5)

    llm.chat = mock_chat

    result = await engine_inst.run("echo hello", mode=AgentMode.TOOL_USE)
    assert result.answer == "Done! Echoed hello."
    assert result.turn_count == 2
    assert len(result.messages) == 5  # system, user, assistant+tool_call, tool_result, assistant

    # Verify tool result is in messages
    tool_msgs = [m for m in result.messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].content == "echo: hello"

    # Persist and verify DB (skip system message)
    session = await db.create_session("test", "chat_tool")
    batch = [(m.role, m.content) for m in result.messages if m.role != "system"]
    await db.append_messages_batch(session.id, batch)

    records = await db.get_messages(session.id)
    assert len(records) == 4
    tool_records = [r for r in records if r.role == "tool"]
    assert len(tool_records) == 1
    assert tool_records[0].content == "echo: hello"


# ---------------------------------------------------------------------------
# Test: Tool call blocked by permission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_blocked_by_permissions():
    """Verify that denied tools produce error results and engine continues."""
    llm = AsyncMock()
    registry = ToolRegistry()
    registry.register(Tool(
        name="echo",
        description="Echo text",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        handler=_echo_handler,
        category="test",
    ))
    # READ_ONLY blocks write tools; echo is not in the write set so we test DENY via rule engine
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)

    engine = AgentEngine(llm=llm, tool_registry=registry, permissions=permissions, max_turns=10)

    call_count = 0

    async def mock_chat(messages, tools=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="tc1", name="bash", args={"command": "rm -rf /"})],
                tokens_used=5,
            )
        return LLMResponse(content="I can't do that.", tool_calls=[], tokens_used=5)

    llm.chat = mock_chat

    result = await engine.run("delete everything", mode=AgentMode.TOOL_USE)
    assert result.answer == "I can't do that."
    # The tool result message should contain a DENIED error
    tool_msgs = [m for m in result.messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert "DENIED" in tool_msgs[0].content


# ---------------------------------------------------------------------------
# Test: Context compression in long conversation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_compression_triggers():
    """Create engine with tiny context_window_size, feed many messages, verify compression."""
    llm = AsyncMock()
    registry = ToolRegistry()
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)

    # Tiny context window to force compression
    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=10,
        context_window_size=50,  # Very small to trigger compression
    )

    # Build a long message list that exceeds the tiny context window
    long_messages = [
        Message(role="system", content="You are a helpful assistant with extensive knowledge."),
    ]
    for i in range(10):
        long_messages.append(
            Message(role="user", content=f"This is a long question number {i} about many things.")
        )
        long_messages.append(
            Message(role="assistant", content=f"This is a long answer number {i} with detailed information.")
        )

    # Verify compression happens
    original_count = len(long_messages)
    compressed = engine._maybe_compress(long_messages)
    assert len(compressed) < original_count
    # The summary message should be present
    summary_msgs = [m for m in compressed if m.role == "system" and "compressed" in m.content.lower()]
    assert len(summary_msgs) == 1
    # Head and tail should be preserved
    assert compressed[0] == long_messages[0]  # system prompt preserved as head


@pytest.mark.asyncio
async def test_no_compression_when_within_budget():
    """Verify compression does not trigger when messages fit within budget."""
    llm = AsyncMock()
    registry = ToolRegistry()
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    engine = AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=permissions,
        max_turns=10,
        context_window_size=8000,
    )

    messages = [
        Message(role="user", content="Short question"),
        Message(role="assistant", content="Short answer"),
    ]
    result = engine._maybe_compress(messages)
    assert result is messages  # Should return the same list (no compression)
