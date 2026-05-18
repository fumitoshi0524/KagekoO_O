"""LLM package — parity with ClawCode clawcode/llm/__init__.py."""

from __future__ import annotations

from .base import (
    BaseProvider, ProviderEvent, ProviderEventType, ProviderResponse,
    TokenUsage, ToolCall, CacheStats,
    ProviderError, RateLimitError, ContextLimitError, AuthenticationError,
    aiter_from_iterator, collect_events,
)

__all__ = [
    "BaseProvider", "ProviderEvent", "ProviderEventType", "ProviderResponse",
    "TokenUsage", "ToolCall", "CacheStats",
    "ProviderError", "RateLimitError", "ContextLimitError", "AuthenticationError",
    "aiter_from_iterator", "collect_events",
]
