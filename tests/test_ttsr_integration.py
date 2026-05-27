from __future__ import annotations

import re
import pytest
from unittest.mock import AsyncMock, MagicMock

from kageko.llm.adapter import LLMAdapter
from kageko.agent.ttsr import StreamRule, StreamInterceptor, Correction


@pytest.mark.asyncio
async def test_stream_chat_with_ttsr():
    adapter = LLMAdapter("test-model", "test-key", "http://localhost:0")
    rule = StreamRule(
        name="no-sorry",
        pattern=re.compile(r"sorry.{0,20}I can't"),
        message="Don't apologize. Provide the solution directly.",
    )
    async def mock_stream(*args, **kwargs):
        yield "I'm sorry, I can't help with that."
    adapter._raw_stream = mock_stream
    results = []
    async for item in adapter.stream_chat([], ttsr_rules=[rule]):
        results.append(item)
    assert any(isinstance(r, Correction) for r in results)


@pytest.mark.asyncio
async def test_stream_chat_without_ttsr():
    adapter = LLMAdapter("test-model", "test-key", "http://localhost:0")
    async def mock_stream(*args, **kwargs):
        yield "Hello"
        yield " world"
    adapter._raw_stream = mock_stream
    results = []
    async for item in adapter.stream_chat([]):
        results.append(item)
    assert results == ["Hello", " world"]
