# src/kageko/llm.py
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from kageko.types import Message, StreamToken, ToolCall


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall]
    tokens_used: int = 0

    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMAdapter:
    """OpenAI-compatible LLM adapter. Works with any provider that implements the OpenAI API."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.7,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        result = []
        for msg in messages:
            d: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                d["tool_calls"] = [tc.to_dict() for tc in msg.tool_calls]
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
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
            "temperature": self.temperature,
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, args=args))

        tokens_used = response.usage.total_tokens if response.usage else 0

        return LLMResponse(content=content, tool_calls=tool_calls, tokens_used=tokens_used)

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamToken]:
        """Stream tokens from the LLM one at a time."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "temperature": self.temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        stream = await self._client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield StreamToken(
                        text="",
                        is_tool_call=True,
                        tool_name=tc.function.name or "",
                        tool_args=tc.function.arguments or "",
                        tool_call_id=tc.id or "",
                    )
            elif delta.content:
                yield StreamToken(
                    text=delta.content,
                    finish_reason=choice.finish_reason or "",
                )
            elif choice.finish_reason:
                yield StreamToken(text="", finish_reason=choice.finish_reason)
