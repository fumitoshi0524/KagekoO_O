"""GLM (Zhipu / Z.ai) OpenAI-compatible adapter.

GLM exposes an OpenAI-shaped Chat Completions API but supports vendor-specific
capabilities that are important for agent/tool workflows:

- Thinking: `thinking={type: enabled|disabled}` with output in `reasoning_content`.
- Preserved thinking: enable with `thinking.clear_thinking = False`, requiring
  the client to return prior `reasoning_content` unmodified in subsequent turns.
- Stream tool calls: enable with `tool_stream=True` when `stream=True` + tools.

We apply these only when tools are present to keep lightweight chat fast.
"""

from __future__ import annotations

from typing import Any

from .adapter import AdapterContext


# QAOA: UniToolCall adapter for GLM
class GLMAdapter:
    vendor = "glm"

    def matches(self, ctx: AdapterContext) -> bool:
        base = (ctx.base_url or "").lower()
        model = (ctx.model or "").lower()
        # Common OpenAI-compatible endpoints for Zhipu / Z.ai
        if "open.bigmodel.cn" in base:
            return True
        if "api.z.ai" in base:
            return True
        # Fallback by model prefix if user uses a custom proxy.
        return model.startswith("glm-")

    def should_inject_reasoning_history(self, *, tools_present: bool) -> bool:
        # For interleaved/preserved thinking tool loops, GLM expects the client
        # to return reasoning_content to keep reasoning coherent.
        return bool(tools_present)

    def patch_request_params(
        self,
        params: dict[str, Any],
        *,
        tools_present: bool,
        stream: bool,
    ) -> dict[str, Any]:
        if not tools_present:
            return params

        extra_body = params.get("extra_body")
        if not isinstance(extra_body, dict):
            extra_body = {}

        thinking = extra_body.get("thinking")
        if not isinstance(thinking, dict):
            thinking = {}

        # Force thinking when tools are present.
        thinking.setdefault("type", "enabled")
        # Enable preserved thinking (vendor doc: clear_thinking False).
        thinking.setdefault("clear_thinking", False)
        extra_body["thinking"] = thinking

        # Stream tool calls to reduce latency when streaming.
        if stream:
            extra_body.setdefault("tool_stream", True)

        params["extra_body"] = extra_body
        return params

    def patch_message_row(
        self,
        row: dict[str, Any],
        *,
        tools_present: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        return row
