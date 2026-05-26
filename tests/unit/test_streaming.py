# tests/unit/test_streaming.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kageko.llm import LLMAdapter
from kageko.types import Message, StreamToken


def test_stream_token_text():
    tok = StreamToken(text="hello", is_tool_call=False)
    assert tok.text == "hello"
    assert not tok.is_tool_call


def test_stream_token_tool_call():
    tok = StreamToken(text="", is_tool_call=True, tool_name="bash", tool_args='{"cmd": "ls"}')
    assert tok.is_tool_call
    assert tok.tool_name == "bash"


@pytest.mark.asyncio
async def test_chat_stream_exists():
    """LLMAdapter must have a chat_stream method."""
    adapter = LLMAdapter(model="test", api_key="fake", base_url="http://localhost")
    assert hasattr(adapter, "chat_stream")
    assert callable(adapter.chat_stream)


@pytest.mark.asyncio
async def test_run_stream_exists():
    """AgentEngine must have a run_stream method."""
    from kageko.agent.loop import AgentEngine
    from kageko.agent.permissions import PermissionPipeline, SecurityMode
    from kageko.tools.registry import ToolRegistry

    llm = MagicMock()
    registry = ToolRegistry()
    permissions = PermissionPipeline(mode=SecurityMode.PERMISSIVE)
    engine = AgentEngine(llm=llm, tool_registry=registry, permissions=permissions)
    assert hasattr(engine, "run_stream")
