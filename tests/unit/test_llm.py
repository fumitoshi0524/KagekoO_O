# tests/unit/test_llm.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from kageko.llm import LLMAdapter, LLMResponse
from kageko.types import Message, ToolCall


@pytest.fixture
def adapter():
    return LLMAdapter(model="gpt-4o", api_key="test-key", base_url="https://api.openai.com/v1")


def test_adapter_init(adapter):
    assert adapter.model == "gpt-4o"
    assert adapter.base_url == "https://api.openai.com/v1"


def test_convert_messages():
    adapter = LLMAdapter(model="gpt-4o", api_key="key")
    messages = [
        Message(role="user", content="hello"),
        Message(role="assistant", content="hi"),
    ]
    result = adapter._convert_messages(messages)
    assert result == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_convert_tool_schemas():
    adapter = LLMAdapter(model="gpt-4o", api_key="key")
    schemas = [
        {
            "name": "file_read",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
    ]
    result = adapter._convert_tools(schemas)
    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "file_read"


@pytest.mark.asyncio
async def test_chat_no_tools(adapter):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello!"
    mock_response.choices[0].message.tool_calls = None
    mock_response.usage.total_tokens = 100

    adapter._client = AsyncMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

    messages = [Message(role="user", content="hello")]
    result = await adapter.chat(messages)
    assert result.content == "Hello!"
    assert result.has_tool_calls() is False
    assert result.tokens_used == 100


@pytest.mark.asyncio
async def test_chat_with_tool_calls(adapter):
    mock_tc = MagicMock()
    mock_tc.id = "call_1"
    mock_tc.function.name = "file_read"
    mock_tc.function.arguments = json.dumps({"path": "test.py"})

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.tool_calls = [mock_tc]
    mock_response.usage.total_tokens = 200

    adapter._client = AsyncMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

    messages = [Message(role="user", content="read test.py")]
    result = await adapter.chat(messages, tools=[{"name": "file_read"}])
    assert result.has_tool_calls() is True
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "file_read"
    assert result.tool_calls[0].args == {"path": "test.py"}
