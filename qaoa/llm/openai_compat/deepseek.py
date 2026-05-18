"""DeepSeek OpenAI-compatible adapter.

DeepSeek exposes an OpenAI-shaped Chat Completions API but:
- Enabling thinking for `deepseek-chat` requires sending `thinking` via OpenAI SDK
  `extra_body`.
- In thinking + tool-call loops, clients must return `reasoning_content` in
  subsequent requests to allow the model to continue its chain-of-thought;
  otherwise the API may return 400 per vendor docs.
"""

from __future__ import annotations

from typing import Any

from .adapter import AdapterContext


# QAOA: UniToolCall adapter for DeepSeek
class DeepSeekAdapter:
    vendor = "deepseek"

    def matches(self, ctx: AdapterContext) -> bool:
        base = (ctx.base_url or "").lower()
        return "api.deepseek.com" in base

    def should_inject_reasoning_history(self, *, tools_present: bool) -> bool:
        # Only needed in the thinking + tool-call loop. The user policy we were
        # given is: enable thinking automatically when tools are present.
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

        # OpenAI SDK: DeepSeek requires `thinking` to be passed via `extra_body`.
        # Keep other vendor params intact if already present.
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
        # No per-row patching needed besides sending reasoning_content when present,
        # which is handled at the Agent history conversion layer.
        return row
