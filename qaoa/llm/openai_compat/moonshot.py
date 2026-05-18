"""Moonshot (Kimi) OpenAI-compatible adapter.

Moonshot API is largely OpenAI-shaped but:
- Prefers ``max_completion_tokens`` over deprecated ``max_tokens``.
- ``kimi-k2.5`` supports a top-level ``thinking`` control and streams
  ``reasoning_content``; sampling fields must not be customized on k2.5 per vendor docs.
"""

from __future__ import annotations

from typing import Any

from .adapter import AdapterContext

_K25_SAMPLING_KEYS = frozenset({
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
})


def _is_kimi_k25_model(model: str) -> bool:
    m = (model or "").lower().strip()
    return m == "kimi-k2.5" or m.startswith("kimi-k2.5-")


# QAOA: UniToolCall adapter for Moonshot
class MoonshotAdapter:
    vendor = "moonshot"

    def matches(self, ctx: AdapterContext) -> bool:
        base = (ctx.base_url or "").lower()
        model = (ctx.model or "").lower()
        if "api.moonshot.cn" in base:
            return True
        if model.startswith("kimi-") or model.startswith("moonshot-v1"):
            return True
        return False

    def should_inject_reasoning_history(self, *, tools_present: bool) -> bool:
        return bool(tools_present)

    def patch_request_params(
        self,
        params: dict[str, Any],
        *,
        tools_present: bool,
        stream: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        # Moonshot: use max_completion_tokens; max_tokens is deprecated (kimi.md).
        if "max_tokens" in params:
            mt = params.pop("max_tokens")
            if "max_completion_tokens" not in params:
                params["max_completion_tokens"] = mt

        model = str(params.get("model") or "")

        if _is_kimi_k25_model(model):
            for k in _K25_SAMPLING_KEYS:
                params.pop(k, None)

        if tools_present and _is_kimi_k25_model(model):
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
