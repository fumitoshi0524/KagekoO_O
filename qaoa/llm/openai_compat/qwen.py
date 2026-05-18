"""Qwen (DashScope) OpenAI-compatible adapter.

Qwen uses OpenAI-compatible chat completions endpoints and returns
`reasoning_content` on thinking-capable models. Most vendor-specific knobs
are non-standard parameters passed through `extra_body`.
"""

from __future__ import annotations

from typing import Any

from .adapter import AdapterContext


# QAOA: UniToolCall adapter for Qwen
class QwenAdapter:
    vendor = "qwen"

    def matches(self, ctx: AdapterContext) -> bool:
        base = (ctx.base_url or "").lower()
        model = (ctx.model or "").lower()

        if "dashscope.aliyuncs.com" in base:
            return True
        if "dashscope-intl.aliyuncs.com" in base:
            return True
        if "dashscope-us.aliyuncs.com" in base:
            return True
        if "dashscope-finance.aliyuncs.com" in base:
            return True

        return (
            model.startswith("qwen-")
            or model.startswith("qwq-")
            or model.startswith("qvq-")
        )

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
        extra_body.setdefault("enable_thinking", True)
        params["extra_body"] = extra_body
        return params

    def patch_message_row(
        self,
        row: dict[str, Any],
        *,
        tools_present: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        return row
