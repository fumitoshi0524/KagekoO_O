"""Base LLM Provider abstraction — parity with ClawCode clawcode/llm/base.py.

This module defines the abstract base class for all LLM providers,
including event types, responses, and the provider interface.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from pydantic import BaseModel


class ProviderEventType(str, Enum):
    """Event types for streaming responses."""
    CONTENT_START = "content_start"
    CONTENT_DELTA = "content_delta"
    THINKING_DELTA = "thinking_delta"
    TOOL_USE_START = "tool_use_start"
    TOOL_USE_STOP = "tool_use_stop"
    COMPLETE = "complete"
    ERROR = "error"
    WARNING = "warning"


@dataclass
class TokenUsage:
    """Token usage information."""
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens + self.cache_read_tokens


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    input: str | dict[str, Any]
    finished: bool = False

    def get_input_dict(self) -> dict[str, Any]:
        if isinstance(self.input, dict):
            return self.input
        try:
            return json.loads(self.input)
        except (json.JSONDecodeError, TypeError):
            return {"raw": self.input}


@dataclass
class ProviderEvent:
    """Event from streaming LLM response."""
    type: ProviderEventType
    content: str = ""
    thinking: str = ""
    tool_call: ToolCall | None = None
    response: ProviderResponse | None = None
    error: Exception | None = None

    @classmethod
    def content_delta(cls, content: str) -> ProviderEvent:
        return cls(type=ProviderEventType.CONTENT_DELTA, content=content)

    @classmethod
    def thinking_delta(cls, thinking: str) -> ProviderEvent:
        return cls(type=ProviderEventType.THINKING_DELTA, thinking=thinking)

    @classmethod
    def tool_use_start(cls, tool_call: ToolCall) -> ProviderEvent:
        return cls(type=ProviderEventType.TOOL_USE_START, tool_call=tool_call)

    @classmethod
    def tool_use_stop(cls) -> ProviderEvent:
        return cls(type=ProviderEventType.TOOL_USE_STOP)

    @classmethod
    def complete(cls, response: ProviderResponse) -> ProviderEvent:
        return cls(type=ProviderEventType.COMPLETE, response=response)

    @classmethod
    def error(cls, error: Exception) -> ProviderEvent:
        return cls(type=ProviderEventType.ERROR, error=error)


@dataclass
class CacheStats:
    """Cache statistics for prompt caching."""
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cached: bool = False

    @property
    def total_cache_tokens(self) -> int:
        return self.cache_read_tokens + self.cache_creation_tokens


@dataclass
class ProviderResponse:
    """Complete response from LLM."""
    content: str
    thinking: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage | None = None
    finish_reason: str = "stop"
    model: str = ""
    cache_stats: CacheStats | None = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self, model: str, api_key: str | None = None,
        base_url: str | None = None, max_tokens: int = 4096,
        system_message: str = "", **kwargs: Any,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.system_message = system_message
        self._extra_options = kwargs

    @abstractmethod
    async def send_messages(
        self, messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        pass

    @abstractmethod
    async def stream_response(
        self, messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        pass

    async def health_check(self) -> bool:
        try:
            await self.send_messages([{"role": "user", "content": "ping"}], tools=None)
            return True
        except Exception:
            return False

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def supports_attachments(self) -> bool:
        return True

    @property
    def supports_thinking(self) -> bool:
        return False

    def get_tool_schema(self, tool_info: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool_info.get("name"),
                "description": tool_info.get("description"),
                "parameters": {
                    "type": "object",
                    "properties": tool_info.get("parameters", {}),
                    "required": tool_info.get("required", []),
                },
            },
        }


class ProviderError(Exception):
    """Base exception for provider errors."""
    def __init__(self, message: str, provider: str | None = None,
                 model: str | None = None, original: Exception | None = None) -> None:
        self.provider = provider
        self.model = model
        self.original = original
        super().__init__(message)


class RateLimitError(ProviderError):
    pass


class ContextLimitError(ProviderError):
    pass


class AuthenticationError(ProviderError):
    pass


async def aiter_from_iterator(iterator: Any) -> AsyncIterator[ProviderEvent]:
    loop = asyncio.get_event_loop()
    while True:
        try:
            item = await loop.run_in_executor(None, next, iterator)
            yield item
        except StopIteration:
            break


async def collect_events(event_stream: AsyncIterator[ProviderEvent]) -> list[ProviderEvent]:
    events = []
    async for event in event_stream:
        events.append(event)
    return events
