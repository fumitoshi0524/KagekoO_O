# tests/unit/test_multi_turn.py
"""Tests for Task 4: System prompt + multi-turn with DB persistence."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from kageko.types import AgentResult, Message, AgentMode, ToolCall
from kageko.agent.loop import AgentEngine
from kageko.agent.permissions import PermissionPipeline, SecurityMode
from kageko.llm import LLMAdapter, LLMResponse
from kageko.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Unit: AgentResult messages field
# ---------------------------------------------------------------------------


def test_agent_result_has_messages():
    """AgentResult must accept and store a messages list."""
    msgs = [Message(role="user", content="hi")]
    result = AgentResult(answer="hi", messages=msgs)
    assert len(result.messages) == 1
    assert result.messages[0].role == "user"


def test_agent_result_messages_default_empty():
    """AgentResult.messages defaults to empty list."""
    result = AgentResult(answer="hi")
    assert result.messages == []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def llm():
    return MagicMock(spec=LLMAdapter)


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.fixture
def engine(llm, registry):
    perms = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    return AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=perms,
        max_turns=10,
        system_prompt="You are Kageko, a helpful AI assistant.",
    )


@pytest.fixture
def engine_no_sp(llm, registry):
    """Engine without system prompt."""
    perms = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    return AgentEngine(
        llm=llm,
        tool_registry=registry,
        permissions=perms,
        max_turns=10,
    )


# ---------------------------------------------------------------------------
# System prompt injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_system_prompt_injected(engine, llm):
    """When system_prompt is set, the first message should be a system message."""
    llm.chat = AsyncMock(return_value=LLMResponse(
        content="Hello!", tool_calls=[], tokens_used=10,
    ))

    result = await engine.run("hi")

    # Check that llm.chat received messages starting with system
    call_args = llm.chat.call_args
    messages = call_args[0][0]
    assert messages[0].role == "system"
    assert "Kageko" in messages[0].content
    assert messages[1].role == "user"
    assert messages[1].content == "hi"


@pytest.mark.asyncio
async def test_system_prompt_not_duplicated(engine, llm):
    """Calling run() multiple times should not duplicate the system prompt."""
    llm.chat = AsyncMock(return_value=LLMResponse(
        content="ok", tool_calls=[], tokens_used=10,
    ))

    # First call with a message list that already has the system prompt
    messages = [
        Message(role="system", content="You are Kageko, a helpful AI assistant."),
        Message(role="user", content="first"),
        Message(role="assistant", content="reply1"),
    ]
    await engine.run(messages)

    call_args = llm.chat.call_args
    sent_messages = call_args[0][0]
    # Should not have duplicate system prompts
    system_count = sum(1 for m in sent_messages if m.role == "system")
    assert system_count == 1


@pytest.mark.asyncio
async def test_no_system_prompt_when_not_configured(engine_no_sp, llm):
    """When system_prompt is empty, no system message should be injected."""
    llm.chat = AsyncMock(return_value=LLMResponse(
        content="Hello!", tool_calls=[], tokens_used=10,
    ))

    result = await engine_no_sp.run("hi")

    call_args = llm.chat.call_args
    messages = call_args[0][0]
    assert messages[0].role == "user"
    assert messages[0].content == "hi"


# ---------------------------------------------------------------------------
# Multi-turn: message list accepted by run()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_accepts_message_list(engine_no_sp, llm):
    """run() should accept a list of Message objects."""
    captured_messages = []

    async def capture_chat(messages, tools=None):
        captured_messages.append(list(messages))
        return LLMResponse(content="reply2", tool_calls=[], tokens_used=10)

    llm.chat = AsyncMock(side_effect=capture_chat)

    messages = [
        Message(role="user", content="first"),
        Message(role="assistant", content="reply1"),
        Message(role="user", content="second"),
    ]
    result = await engine_no_sp.run(messages)

    sent = captured_messages[0]
    assert len(sent) == 3
    assert sent[0].content == "first"
    assert sent[2].content == "second"
    assert result.answer == "reply2"


@pytest.mark.asyncio
async def test_run_still_accepts_string(engine_no_sp, llm):
    """run() should still work with a plain string (backward compat)."""
    captured_messages = []

    async def capture_chat(messages, tools=None):
        captured_messages.append(list(messages))
        return LLMResponse(content="hi back", tool_calls=[], tokens_used=10)

    llm.chat = AsyncMock(side_effect=capture_chat)

    result = await engine_no_sp.run("hello")

    assert result.answer == "hi back"
    sent = captured_messages[0]
    assert len(sent) == 1
    assert sent[0].role == "user"
    assert sent[0].content == "hello"


@pytest.mark.asyncio
async def test_multi_turn_preserves_history(engine_no_sp, llm):
    """Second turn should see the full conversation history."""
    captured_calls = []

    async def capture_chat(messages, tools=None):
        captured_calls.append(list(messages))
        return LLMResponse(content="reply", tool_calls=[], tokens_used=10)

    llm.chat = AsyncMock(side_effect=capture_chat)

    # Simulate multi-turn: pass full history each time
    history = [Message(role="user", content="what is 2+2?")]
    await engine_no_sp.run(history)

    # Second turn: append assistant reply and new user message
    history.append(Message(role="assistant", content="4"))
    history.append(Message(role="user", content="what about 3+3?"))
    await engine_no_sp.run(history)

    second_call_msgs = captured_calls[1]
    assert len(second_call_msgs) == 3
    assert second_call_msgs[0].content == "what is 2+2?"
    assert second_call_msgs[1].content == "4"
    assert second_call_msgs[2].content == "what about 3+3?"


@pytest.mark.asyncio
async def test_result_contains_messages(engine_no_sp, llm):
    """AgentResult should contain the full message list after run()."""
    llm.chat = AsyncMock(return_value=LLMResponse(
        content="Hello!", tool_calls=[], tokens_used=10,
    ))

    result = await engine_no_sp.run("hi")
    assert len(result.messages) >= 2  # user + assistant at minimum
    assert result.messages[0].role == "user"
    assert result.messages[-1].role == "assistant"
    assert result.messages[-1].content == "Hello!"


# ---------------------------------------------------------------------------
# run_stream with message list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_stream_accepts_message_list(engine_no_sp, llm):
    """run_stream() should accept a list of Message objects."""

    async def fake_stream(messages, tools=None):
        from kageko.types import StreamToken
        yield StreamToken(text="hello", finish_reason="stop")

    llm.chat_stream = fake_stream

    messages = [
        Message(role="user", content="first"),
        Message(role="assistant", content="reply"),
        Message(role="user", content="second"),
    ]

    tokens = []
    async for tok in engine_no_sp.run_stream(messages):
        tokens.append(tok)

    text_tokens = [t for t in tokens if hasattr(t, "text") and t.text]
    assert any("hello" in t.text for t in text_tokens)
