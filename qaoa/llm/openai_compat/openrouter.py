"""OpenRouter OpenAI-compatible adapter.

OpenRouter can be accessed via OpenAI SDK by pointing base_url to
`https://openrouter.ai/api/v1`. Some OpenRouter capabilities are passed
through OpenAI SDK's `extra_body`.
"""

from __future__ import annotations

from typing import Any

from .adapter import AdapterContext


# QAOA: UniToolCall adapter for OpenRouter
class OpenRouterAdapter:
    vendor = "openrouter"

    _EXTRA_BODY_KEYS = (
        "models",
        "provider",
        "plugins",
        "transforms",
        "route",
        "reasoning",
        "include_reasoning",
        "parallel_tool_calls",
    )

    def matches(self, ctx: AdapterContext) -> bool:
        base = (ctx.base_url or "").lower()
        return "openrouter.ai" in base

    def should_inject_reasoning_history(self, *, tools_present: bool) -> bool:
        # Keep interleaved thinking continuity in tool loops.
        return bool(tools_present)

    def patch_request_params(
        self,
        params: dict[str, Any],
        *,
        tools_present: bool,
        stream: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        extra_body = params.get("extra_body")
        if not isinstance(extra_body, dict):
            extra_body = {}

        # Move OpenRouter-only fields into `extra_body` for OpenAI SDK compatibility.
        for k in self._EXTRA_BODY_KEYS:
            if k in params:
                extra_body.setdefault(k, params.pop(k))

        # Default include_reasoning for tool loops so thinking can be consumed
        # by current agent framework without per-model branching.
        if tools_present:
            extra_body.setdefault("include_reasoning", True)

        if extra_body:
            params["extra_body"] = extra_body
        return params

    def patch_message_row(
        self,
        row: dict[str, Any],
        *,
        tools_present: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        return row
