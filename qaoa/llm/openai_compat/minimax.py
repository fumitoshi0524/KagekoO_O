"""MiniMax OpenAI-compatible adapter.

MiniMax exposes a chat-completions compatible endpoint and recommends
`reasoning_split=true` to return thinking in `reasoning_details`.
"""

from __future__ import annotations

from typing import Any

from .adapter import AdapterContext


# QAOA: UniToolCall adapter for MiniMax
class MiniMaxAdapter:
    vendor = "minimax"

    def matches(self, ctx: AdapterContext) -> bool:
        base = (ctx.base_url or "").lower()
        model = (ctx.model or "").lower()
        if "api.minimaxi.com" in base:
            return True
        return (
            model.startswith("minimax-")
            or model.startswith("abab")
            or model.startswith("minimax/")
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
        extra_body.setdefault("reasoning_split", True)
        params["extra_body"] = extra_body

        if "n" in params and params.get("n") != 1:
            params["n"] = 1

        return params

    def patch_message_row(
        self,
        row: dict[str, Any],
        *,
        tools_present: bool,  # noqa: ARG002
    ) -> dict[str, Any]:
        return row
