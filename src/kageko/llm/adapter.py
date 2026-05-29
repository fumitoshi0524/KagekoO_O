# src/kageko/llm/adapter.py
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from kageko.llm.providers import ProviderProfile, ModelInfo, get_model_info
from kageko.types import Message, StreamToken, ToolCall

logger = logging.getLogger("kageko.llm")


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall]
    tokens_used: int = 0
    reasoning_content: str | None = None

    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMAdapter:
    """OpenAI-compatible LLM adapter. Works with any provider that implements the OpenAI API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        provider: ProviderProfile | None = None,
        model_info: ModelInfo | None = None,
    ):
        if provider:
            self.model = model if model is not None else provider.default_model
            self.api_key = api_key if api_key is not None else provider.api_key
            self.base_url = base_url if base_url is not None and base_url != "https://api.openai.com/v1" else provider.base_url
            self.max_retries = provider.max_retries
            self._provider = provider
            self._model_info = model_info or get_model_info(provider, self.model)
        else:
            self.model = model or ""
            self.api_key = api_key or ""
            self.base_url = base_url or "https://api.openai.com/v1"
            self.max_retries = max_retries
            self._provider = None
            self._model_info = model_info
        self.temperature = temperature
        self.retry_delay = retry_delay
        self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def _retry(self, coro_factory):
        """Retry a coroutine factory on transient errors with exponential backoff."""
        from openai import RateLimitError, APITimeoutError, APIConnectionError
        retryable = (RateLimitError, APITimeoutError, APIConnectionError)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await coro_factory()
            except retryable as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt + 1, self.max_retries, e, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "LLM call failed after %d attempts: %s",
                        self.max_retries, e,
                    )
                    raise

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        result = []
        for msg in messages:
            d: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                d["tool_calls"] = [tc.to_dict() for tc in msg.tool_calls]
            if msg.tool_call_id is not None:
                d["tool_call_id"] = msg.tool_call_id
            if msg.role == "tool" and msg.tool_name:
                d["name"] = msg.tool_name
            if msg.reasoning_content is not None:
                d["reasoning_content"] = msg.reasoning_content
            result.append(d)
        return result

    def _convert_tools(self, schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"type": "function", "function": schema} for schema in schemas]

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
        }
        if self._model_info is None or self._model_info.supports_temperature:
            kwargs["temperature"] = self.temperature
        if tools and (self._model_info is None or self._model_info.supports_tools):
            kwargs["tools"] = self._convert_tools(tools)

        response = await self._retry(lambda: self._client.chat.completions.create(**kwargs))

        choice = response.choices[0]
        content = choice.message.content or ""
        reasoning_content = getattr(choice.message, "reasoning_content", None) or None

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    logger.warning(
                        "Failed to parse tool args for %s: %r",
                        tc.function.name, tc.function.arguments,
                    )
                    args = {}
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, args=args))

        tokens_used = response.usage.total_tokens if response.usage else 0

        return LLMResponse(content=content, tool_calls=tool_calls, tokens_used=tokens_used, reasoning_content=reasoning_content)

    async def _raw_stream(self, messages: list[Message], tools: list[dict[str, Any]] | None = None) -> AsyncIterator[str]:
        """Internal raw string stream from the LLM."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "stream": True,
        }
        if self._model_info is None or self._model_info.supports_temperature:
            kwargs["temperature"] = self.temperature
        if tools and (self._model_info is None or self._model_info.supports_tools):
            kwargs["tools"] = self._convert_tools(tools)

        stream = await self._retry(lambda: self._client.chat.completions.create(**kwargs))

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def stream_chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        *,
        ttsr_rules: list | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion. Optionally apply TTSR stream rules."""
        raw_stream = self._raw_stream(messages, tools)
        if ttsr_rules:
            from kageko.agent.ttsr import StreamInterceptor
            interceptor = StreamInterceptor(ttsr_rules)
            async for item in interceptor.intercept(raw_stream):
                yield item
        else:
            async for token in raw_stream:
                yield token

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamToken]:
        """Stream tokens from the LLM one at a time.

        Tool call deltas are accumulated by index because some providers
        (e.g. DeepSeek) stream them across multiple chunks: the first chunk
        carries id + name, subsequent chunks carry only index + arguments.
        Consolidated StreamTokens are emitted after the stream body ends.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
        }
        if self._model_info is None or self._model_info.supports_temperature:
            kwargs["temperature"] = self.temperature
        kwargs["stream"] = True
        if tools and (self._model_info is None or self._model_info.supports_tools):
            kwargs["tools"] = self._convert_tools(tools)

        stream = await self._retry(lambda: self._client.chat.completions.create(**kwargs))

        total_tokens = 0
        tool_call_buf: dict[int, dict] = {}  # index -> {id, name, args_str}
        stream_finish_reason = ""

        async for chunk in stream:
            if chunk.usage and chunk.usage.total_tokens:
                total_tokens = chunk.usage.total_tokens
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            reasoning = getattr(delta, "reasoning_content", "") or ""
            if choice.finish_reason:
                stream_finish_reason = choice.finish_reason

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = getattr(tc, "index", None)
                    if idx is None:
                        idx = len(tool_call_buf)
                    if idx not in tool_call_buf:
                        tool_call_buf[idx] = {"id": "", "name": "", "args_str": ""}
                    buf = tool_call_buf[idx]
                    if tc.id:
                        buf["id"] = tc.id
                    if tc.function and tc.function.name:
                        buf["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        buf["args_str"] += tc.function.arguments
                if reasoning:
                    yield StreamToken(text="", reasoning_content=reasoning)
            elif reasoning:
                yield StreamToken(
                    text="",
                    reasoning_content=reasoning,
                )
            elif delta.content:
                yield StreamToken(
                    text=delta.content,
                    finish_reason=choice.finish_reason or "",
                )
            elif choice.finish_reason:
                yield StreamToken(text="", finish_reason=choice.finish_reason)

        # Emit accumulated tool calls (only those with a name)
        ordered = sorted(tool_call_buf.keys())
        for i, idx in enumerate(ordered):
            tc = tool_call_buf[idx]
            if tc["name"]:
                yield StreamToken(
                    text="",
                    is_tool_call=True,
                    tool_name=tc["name"],
                    tool_args=tc["args_str"],
                    tool_call_id=tc["id"],
                    finish_reason=stream_finish_reason if i == len(ordered) - 1 else "",
                )

        if total_tokens:
            yield StreamToken(text="", tokens_used=total_tokens)
