"""Volcengine Ark OpenAI-compatible adapter.

Volcengine primarily documents the Responses API, but OpenAI SDK users can
still call chat-completions compatible endpoints through a custom `base_url`.
This adapter keeps the current OpenAIProvider contract and injects only the
minimum vendor-specific knobs needed by tool workflows.
"""

from __future__ import annotations

from typing import Any

from .adapter import AdapterContext


# QAOA: UniToolCall adapter for Volcengine
class VolcengineAdapter:
    vendor = "volcengine"

    def matches(self, ctx: AdapterContext) -> bool:
        base = (ctx.base_url or "").lower()
        model = (ctx.model or "").lower()

        # Common Ark gateway patterns.
        if "volces.com" in base or "volcengine.com" in base:
            return True
        # Fallback for proxy/custom base_url cases.
        return model.startswith("doubao-") or model.startswith("ep-")

    def should_inject_reasoning_history(self, *, tools_present: bool) -> bool:
        return bool(tools_present)

    def patch_request_params(
        self,
        params: dict[str, Any],
        *,
        tools_present: bool,
        stream: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        if not tools_present:
            return params

        extra_body = params.get("extra_body")
        if not isinstance(extra_body, dict):
            extra_body = {}
        thinking = extra_body.get("thinking")
        if not isinstance(thinking, dict):
            thinking = {}
        thinking.setdefault("type", "enabled")
        extra_body["thinking"] = thinking
        params["extra_body"] = extra_body
        return params

    def patch_message_row(
        self,
        row: dict[str, Any],
        *,
        tools_present: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        return row
