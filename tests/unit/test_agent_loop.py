# tests/unit/test_agent_loop.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from kageko.agent.loop import AgentEngine
from kageko.agent.permissions import PermissionPipeline, Decision, SecurityMode
from kageko.llm import LLMAdapter, LLMResponse
from kageko.tools.registry import ToolRegistry, Tool
from kageko.types import Message, AgentMode, ToolCall


@pytest.fixture
def tool_registry():
    registry = ToolRegistry()

    async def echo_handler(args):
        return f"echo: {args.get('text', '')}"

    registry.register(Tool(
        name="echo",
        description="Echo text",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        handler=echo_handler,
        category="system",
    ))
    return registry


@pytest.fixture
def llm_adapter():
    adapter = MagicMock(spec=LLMAdapter)
    return adapter


@pytest.fixture
def engine(llm_adapter, tool_registry):
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    return AgentEngine(
        llm=llm_adapter,
        tool_registry=tool_registry,
        permissions=permissions,
        max_turns=10,
    )


@pytest.mark.asyncio
async def test_tool_use_mode_simple_answer(engine, llm_adapter):
    llm_adapter.chat = AsyncMock(return_value=LLMResponse(
        content="Hello!",
        tool_calls=[],
        tokens_used=50,
    ))
    result = await engine.run("hi", mode=AgentMode.TOOL_USE)
    assert result.answer == "Hello!"
    assert result.turn_count == 1


@pytest.mark.asyncio
async def test_tool_use_mode_with_tool_call(engine, llm_adapter):
    llm_adapter.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "hello"})
        ], tokens_used=30),
        LLMResponse(content="The echo said: echo: hello", tool_calls=[], tokens_used=40),
    ])
    result = await engine.run("echo hello", mode=AgentMode.TOOL_USE)
    assert result.answer == "The echo said: echo: hello"
    assert result.turn_count == 2


@pytest.mark.asyncio
async def test_qaoa_mode_records_trajectory(engine, llm_adapter):
    llm_adapter.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "test"})
        ], tokens_used=30),
        LLMResponse(content="result", tool_calls=[], tokens_used=20),
    ])
    result = await engine.run("echo test", mode=AgentMode.QAOA)
    assert result.answer == "result"
    assert result.trajectory is not None
    assert len(result.trajectory.steps) == 1
    assert result.trajectory.steps[0].action.name == "echo"
    assert result.trajectory.steps[0].observation.content == "echo: test"


@pytest.mark.asyncio
async def test_max_turns_stops_loop(engine, llm_adapter):
    engine.max_turns = 2
    llm_adapter.chat = AsyncMock(return_value=LLMResponse(
        content="",
        tool_calls=[ToolCall(id="c1", name="echo", args={"text": "loop"})],
        tokens_used=10,
    ))
    result = await engine.run("loop", mode=AgentMode.TOOL_USE)
    assert result.turn_count == 2


@pytest.mark.asyncio
async def test_permission_denied_skips_tool(engine, llm_adapter):
    engine.permissions.mode = SecurityMode.READ_ONLY
    llm_adapter.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "hi"})
        ], tokens_used=20),
        LLMResponse(content="cant do that", tool_calls=[], tokens_used=10),
    ])
    result = await engine.run("echo hi", mode=AgentMode.TOOL_USE)
    assert result.answer == "cant do that"
