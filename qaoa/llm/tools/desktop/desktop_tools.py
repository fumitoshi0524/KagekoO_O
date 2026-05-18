"""BaseTool wrappers for desktop (Computer Use style) tools."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..base import BaseTool, ToolCall, ToolContext, ToolInfo, ToolResponse
from .desktop_utils import (
    DESKTOP_TOOL_SCHEMAS,
    desktop_click,
    desktop_key,
    desktop_move,
    desktop_screenshot,
    desktop_type,
)

_desktop_action_ts: list[float] = []
_desktop_action_ts_by_session: dict[str, list[float]] = {}


def _json_tool_result_is_error(content: str) -> bool:
    """True when tool fn returned JSON with ``\"ok\": false`` (soft failure)."""
    s = (content or "").strip()
    if not s.startswith("{"):
        return False
    try:
        d = json.loads(s)
    except json.JSONDecodeError:
        return False
    return isinstance(d, dict) and d.get("ok") is False


def _consume_desktop_rate_limit(session_id: str | None) -> tuple[bool, str | None]:
    from ....config.settings import get_settings

    desktop = get_settings().desktop
    cap = getattr(desktop, "max_actions_per_minute", None)
    if cap is None or cap <= 0:
        return True, None
    scope = getattr(desktop, "rate_limit_scope", None) or "global"
    now = time.time()
    if scope == "session":
        global _desktop_action_ts_by_session
        key = (session_id or "").strip() or "__default__"
        lst = _desktop_action_ts_by_session.setdefault(key, [])
        lst[:] = [t for t in lst if now - t < 60.0]
        if len(lst) >= int(cap):
            return False, f"desktop rate limit: max {cap} actions per minute (session scope)"
        lst.append(now)
        return True, None
    global _desktop_action_ts
    _desktop_action_ts = [t for t in _desktop_action_ts if now - t < 60.0]
    if len(_desktop_action_ts) >= int(cap):
        return False, f"desktop rate limit: max {cap} actions per minute"
    _desktop_action_ts.append(now)
    return True, None


def _schema_to_tool_info(schema: dict[str, Any]) -> ToolInfo:
    params = schema.get("parameters") or {}
    required = params.get("required") or []
    return ToolInfo(
        name=schema["name"],
        description=schema.get("description", ""),
        parameters=params,
        required=required,
        category="operations",
        domain="technology",
    )


def _find_desktop_schema(name: str) -> dict[str, Any]:
    for s in DESKTOP_TOOL_SCHEMAS:
        if s.get("name") == name:
            return s
    raise KeyError(f"Missing desktop tool schema: {name}")


_INT_PARAMS = frozenset({"left", "top", "width", "height", "x", "y", "clicks", "monitor_index"})
_FLOAT_PARAMS = frozenset({"interval", "duration"})


def _coerce_desktop_kwargs(params: dict[str, Any], arg_map: dict[str, str]) -> dict[str, Any]:
    """Coerce LLM tool args (often JSON numbers as float) to types expected by desktop_*."""
    out: dict[str, Any] = {}
    for param_key, fn_arg in arg_map.items():
        if param_key not in params or params[param_key] is None:
            continue
        v = params[param_key]
        if param_key in _INT_PARAMS:
            out[fn_arg] = int(round(float(v)))
        elif param_key in _FLOAT_PARAMS:
            out[fn_arg] = float(v)
        else:
            out[fn_arg] = v
    return out


@dataclass(frozen=True)
class _DesktopFnSpec:
    tool_name: str
    schema_name: str
    fn: Callable[..., str]
    arg_map: dict[str, str]


class _SyncStringDesktopTool(BaseTool):
    """Run synchronous desktop helpers in a thread pool."""

    def __init__(self, *, tool_info: ToolInfo, fn: Callable[..., str], arg_map: dict[str, str]) -> None:
        self._tool_info = tool_info
        self._fn = fn
        self._arg_map = arg_map

    def info(self) -> ToolInfo:
        return self._tool_info

    @property
    def requires_permission(self) -> bool:
        return True

    @property
    def is_dangerous(self) -> bool:
        return True

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        params = call.get_input_dict()
        ok_rl, rl_msg = _consume_desktop_rate_limit(context.session_id)
        if not ok_rl:
            return ToolResponse(
                content=json.dumps({"ok": False, "error": rl_msg}, ensure_ascii=False),
                is_error=True,
            )
        try:
            kwargs = _coerce_desktop_kwargs(params, self._arg_map)
            out = await asyncio.to_thread(self._fn, **kwargs)
            is_err = _json_tool_result_is_error(out)
            return ToolResponse(content=out, is_error=is_err)
        except Exception as e:
            return ToolResponse(
                content=json.dumps({"error": str(e)}, ensure_ascii=False),
                is_error=True,
            )


def create_desktop_tools(permissions: Any = None) -> list[BaseTool]:
    """Create desktop_* tools when :func:`check_desktop_requirements` is true."""
    del permissions

    tool_specs: list[_DesktopFnSpec] = [
        _DesktopFnSpec(
            tool_name="desktop_screenshot",
            schema_name="desktop_screenshot",
            fn=desktop_screenshot,
            arg_map={
                "left": "left",
                "top": "top",
                "width": "width",
                "height": "height",
                "monitor_index": "monitor_index",
            },
        ),
        _DesktopFnSpec(
            tool_name="desktop_move",
            schema_name="desktop_move",
            fn=desktop_move,
            arg_map={"x": "x", "y": "y", "duration": "duration"},
        ),
        _DesktopFnSpec(
            tool_name="desktop_click",
            schema_name="desktop_click",
            fn=desktop_click,
            arg_map={"x": "x", "y": "y", "button": "button", "clicks": "clicks"},
        ),
        _DesktopFnSpec(
            tool_name="desktop_type",
            schema_name="desktop_type",
            fn=desktop_type,
            arg_map={"text": "text", "interval": "interval"},
        ),
        _DesktopFnSpec(
            tool_name="desktop_key",
            schema_name="desktop_key",
            fn=desktop_key,
            arg_map={"keys": "keys"},
        ),
    ]

    tools: list[BaseTool] = []
    for spec in tool_specs:
        schema = _find_desktop_schema(spec.schema_name)
        tool_info = _schema_to_tool_info(schema)
        tools.append(
            _SyncStringDesktopTool(
                tool_info=tool_info,
                fn=spec.fn,
                arg_map=spec.arg_map,
            )
        )
    return tools


__all__ = ["create_desktop_tools"]
