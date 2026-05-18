"""OpenAI-compatible request/message adapters.

Some vendors expose an OpenAI-shaped API via a custom `base_url` but require
extra request parameters or message fields to enable features (e.g. DeepSeek
thinking + tool use requires returning `reasoning_content` in subsequent turns).

This module defines a small adapter interface so `OpenAIProvider` can remain
the single OpenAI SDK integration point while supporting vendor quirks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


# QAOA: UniToolCall adapter registry
@dataclass(frozen=True)
class AdapterContext:
    """Context used by compatibility adapters."""

    model: str
    base_url: str | None


class OpenAICompatAdapter(Protocol):
    """Hook points for OpenAI-compatible vendors."""

    vendor: str

    def matches(self, ctx: AdapterContext) -> bool:
        """Return True when this adapter should be used."""

    def should_inject_reasoning_history(self, *, tools_present: bool) -> bool:
        """Whether to send prior reasoning/thinking back in request messages."""

    def patch_request_params(
        self,
        params: dict[str, Any],
        *,
        tools_present: bool,
        stream: bool,
    ) -> dict[str, Any]:
        """Return patched request params for the OpenAI SDK call."""

    def patch_message_row(
        self,
        row: dict[str, Any],
        *,
        tools_present: bool,
    ) -> dict[str, Any]:
        """Patch a single OpenAI-shaped message row before sending."""


class NullAdapter:
    vendor = "none"

    def matches(self, ctx: AdapterContext) -> bool:  # noqa: ARG002
        return True

    def should_inject_reasoning_history(self, *, tools_present: bool) -> bool:  # noqa: ARG002
        return False

    def patch_request_params(
        self,
        params: dict[str, Any],
        *,
        tools_present: bool,  # noqa: ARG002
        stream: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        return params

    def patch_message_row(
        self,
        row: dict[str, Any],
        *,
        tools_present: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        return row


def select_openai_compat_adapter(ctx: AdapterContext) -> OpenAICompatAdapter:
    """Select adapter based on base_url/model.

    Kept intentionally simple: match by `base_url` host substring first.
    """

    from .deepseek import DeepSeekAdapter
    from .glm import GLMAdapter
    from .minimax import MiniMaxAdapter
    from .moonshot import MoonshotAdapter
    from .openrouter import OpenRouterAdapter
    from .qwen import QwenAdapter
    from .volcengine import VolcengineAdapter

    adapters: list[OpenAICompatAdapter] = [
        OpenRouterAdapter(),
        DeepSeekAdapter(),
        GLMAdapter(),
        MiniMaxAdapter(),
        MoonshotAdapter(),
        QwenAdapter(),
        VolcengineAdapter(),
    ]

    for a in adapters:
        try:
            if a.matches(ctx):
                return a
        except Exception:
            continue
    return NullAdapter()
