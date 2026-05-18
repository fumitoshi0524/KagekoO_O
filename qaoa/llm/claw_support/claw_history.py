"""Map Kageko :class:`~qaoa.message.Message` history to OpenAI-style ``list[dict]``.

Reference agent stacks often keep conversation as ``list[dict]`` with ``role`` / ``content`` /
``tool_calls`` / ``tool_call_id``. This module is a thin adapter for telemetry, tests,
and future bridges — the live ReAct loop still uses :class:`~qaoa.message.Message`.
"""

from __future__ import annotations

import json
from typing import Any

from ...message import (
    Message,
    MessageRole,
    TextContent,
    ToolCallContent,
)

__all__ = ["messages_to_openai_style"]


def _tool_call_openai_dict(tc: ToolCallContent) -> dict[str, Any]:
    inp = tc.input
    if isinstance(inp, dict):
        try:
            arg_str = json.dumps(inp, ensure_ascii=False)
        except (TypeError, ValueError):
            arg_str = "{}"
    elif isinstance(inp, str):
        arg_str = inp
    else:
        arg_str = "{}"
    return {
        "id": tc.id,
        "type": "function",
        "function": {"name": tc.name, "arguments": arg_str},
    }


def messages_to_openai_style(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert Kageko messages to OpenAI chat-completions shaped rows.

    - ``user`` / ``system``: ``content`` is plain text from text parts.
    - ``assistant``: ``content`` plus optional ``tool_calls`` when tool_use parts exist.
    - ``tool``: one row per persisted tool result (``TOOL`` messages store a JSON list).

    Thinking parts are omitted; attach separately if you need reasoning traces.
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.role
        if role == MessageRole.SYSTEM:
            text = "".join(p.content for p in msg.parts if isinstance(p, TextContent))
            out.append({"role": "system", "content": text})
            continue
        if role == MessageRole.USER:
            text = "".join(p.content for p in msg.parts if isinstance(p, TextContent))
            out.append({"role": "user", "content": text})
            continue
        if role == MessageRole.ASSISTANT:
            text = "".join(p.content for p in msg.parts if isinstance(p, TextContent))
            tcs = msg.tool_calls()
            row: dict[str, Any] = {"role": "assistant", "content": text or None}
            if tcs:
                row["tool_calls"] = [_tool_call_openai_dict(tc) for tc in tcs]
            if msg.model:
                row["model"] = msg.model
            out.append(row)
            continue
        if role == MessageRole.TOOL:
            raw = "".join(p.content for p in msg.parts if isinstance(p, TextContent))
            if not raw.strip():
                continue
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": "",
                        "content": raw,
                    }
                )
                continue
            if isinstance(parsed, list):
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    tid = item.get("tool_call_id", "")
                    content = item.get("content", "")
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": tid,
                            "content": content if isinstance(content, str) else str(content),
                        }
                    )
            else:
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": "",
                        "content": raw,
                    }
                )
            continue
    return out
