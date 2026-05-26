import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from kageko.llm import LLMAdapter


@pytest.mark.asyncio
async def test_retry_on_rate_limit():
    """LLMAdapter must retry on RateLimitError."""
    adapter = LLMAdapter(model="test", api_key="fake", base_url="http://localhost", max_retries=3)

    from openai import RateLimitError
    # Mock to raise RateLimitError twice then succeed
    call_count = 0
    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError("rate limited", response=MagicMock(), body=None)
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "success"
        response.choices[0].message.tool_calls = None
        response.choices[0].finish_reason = "stop"
        response.usage = MagicMock()
        response.usage.total_tokens = 10
        return response

    with patch.object(adapter._client.chat.completions, "create", mock_create):
        from kageko.types import Message
        result = await adapter.chat([Message(role="user", content="hi")])

    assert result.content == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_no_retry_on_auth_error():
    """LLMAdapter must NOT retry on AuthenticationError."""
    adapter = LLMAdapter(model="test", api_key="fake", base_url="http://localhost", max_retries=3)

    from openai import AuthenticationError
    async def mock_create(**kwargs):
        raise AuthenticationError("bad key", response=MagicMock(), body=None)

    with patch.object(adapter._client.chat.completions, "create", mock_create):
        from kageko.types import Message
        with pytest.raises(AuthenticationError):
            await adapter.chat([Message(role="user", content="hi")])


@pytest.mark.asyncio
async def test_retry_exhausted_raises():
    """LLMAdapter must raise after max retries exhausted."""
    adapter = LLMAdapter(model="test", api_key="fake", base_url="http://localhost", max_retries=2)

    from openai import APITimeoutError
    async def mock_create(**kwargs):
        raise APITimeoutError(request=MagicMock())

    with patch.object(adapter._client.chat.completions, "create", mock_create):
        from kageko.types import Message
        with pytest.raises(APITimeoutError):
            await adapter.chat([Message(role="user", content="hi")])


@pytest.mark.asyncio
async def test_successful_no_retry():
    """LLMAdapter must not retry on success."""
    adapter = LLMAdapter(model="test", api_key="fake", base_url="http://localhost", max_retries=3)

    call_count = 0
    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "ok"
        response.choices[0].message.tool_calls = None
        response.choices[0].finish_reason = "stop"
        response.usage = MagicMock()
        response.usage.total_tokens = 5
        return response

    with patch.object(adapter._client.chat.completions, "create", mock_create):
        from kageko.types import Message
        result = await adapter.chat([Message(role="user", content="hi")])

    assert result.content == "ok"
    assert call_count == 1
