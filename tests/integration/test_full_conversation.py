import pytest
from unittest.mock import AsyncMock
from kageko.agent.loop import AgentEngine
from kageko.agent.permissions import PermissionPipeline, SecurityMode
from kageko.llm import LLMAdapter, LLMResponse
from kageko.tools.registry import ToolRegistry, Tool
from kageko.tools.builtin import BUILTIN_TOOLS
from kageko.types import AgentMode, ToolCall, Message
from kageko.data.qaoa_export import QAOAExporter


@pytest.fixture
def engine_with_tools():
    llm = AsyncMock(spec=LLMAdapter)
    registry = ToolRegistry()
    for t in BUILTIN_TOOLS:
        registry.register(Tool(
            name=t["name"],
            description=t["description"],
            parameters=t["parameters"],
            handler=t["fn"],
            category=t["category"],
        ))
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    return AgentEngine(llm=llm, tool_registry=registry, permissions=permissions, max_turns=10), llm


@pytest.mark.asyncio
async def test_full_tool_use_conversation(engine_with_tools):
    engine, llm = engine_with_tools
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="file_read", args={"path": "config.py"})
        ], tokens_used=30),
        LLMResponse(content="The config model is gpt-4o", tool_calls=[], tokens_used=50),
    ])

    result = await engine.run("What model is configured?", mode=AgentMode.TOOL_USE)
    assert result.answer == "The config model is gpt-4o"
    assert result.turn_count == 2
    assert result.tokens_used == 80


@pytest.mark.asyncio
async def test_qaoa_mode_with_trajectory_export(engine_with_tools, tmp_path):
    engine, llm = engine_with_tools
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "test"})
        ], tokens_used=20),
        LLMResponse(content="Echoed: test", tool_calls=[], tokens_used=30),
    ])

    result = await engine.run("echo test", mode=AgentMode.QAOA)
    assert result.trajectory is not None
    assert len(result.trajectory.steps) == 1
    assert result.trajectory.steps[0].action.name == "echo"
    assert result.trajectory.answer == "Echoed: test"

    exporter = QAOAExporter(str(tmp_path / "export.jsonl"))
    exporter.export(result.trajectory)
    exporter.flush()

    records = exporter.load_all()
    assert len(records) == 1
    assert records[0]["query"] == "echo test"
    assert records[0]["answer"] == "Echoed: test"


@pytest.mark.asyncio
async def test_parallel_tool_calls(engine_with_tools):
    engine, llm = engine_with_tools
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="echo", args={"text": "one"}),
            ToolCall(id="c2", name="echo", args={"text": "two"}),
        ], tokens_used=30),
        LLMResponse(content="Both echoed", tool_calls=[], tokens_used=20),
    ])

    result = await engine.run("echo one and two", mode=AgentMode.TOOL_USE)
    assert result.answer == "Both echoed"
    assert result.turn_count == 2


@pytest.mark.asyncio
async def test_security_blocks_dangerous_command(engine_with_tools):
    engine, llm = engine_with_tools
    engine.permissions.mode = SecurityMode.INTERACTIVE
    llm.chat = AsyncMock(side_effect=[
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="bash", args={"command": "rm -rf /"})
        ], tokens_used=10),
        LLMResponse(content="I can't do that", tool_calls=[], tokens_used=10),
    ])

    result = await engine.run("delete everything", mode=AgentMode.TOOL_USE)
    assert result.answer == "I can't do that"
