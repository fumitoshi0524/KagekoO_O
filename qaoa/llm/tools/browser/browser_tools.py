"""Kageko BaseTool wrappers for migrated browser/web tools.

These tools expose the same tool names as the upstream tool registry
(``browser_*`` / ``web_search`` / ``web_extract``) so the LLM can keep
requesting them, while Kageko executes the underlying local functions.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
import inspect
from typing import Any, Callable

from ..base import BaseTool, ToolCall, ToolContext, ToolInfo, ToolResponse
from .browser_utils import (
    BROWSER_TOOL_SCHEMAS,
    browser_back,
    browser_click,
    browser_console,
    browser_close,
    browser_get_images,
    browser_navigate,
    browser_press,
    browser_snapshot,
    browser_scroll,
    browser_type,
    browser_vision,
    check_browser_requirements,
)
from .web_utils import (
    WEB_EXTRACT_SCHEMA,
    WEB_SEARCH_SCHEMA,
    check_web_api_key,
    web_extract_tool,
    web_search_tool,
)


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


def _find_browser_schema(name: str) -> dict[str, Any]:
    for s in BROWSER_TOOL_SCHEMAS:
        if s.get("name") == name:
            return s
    raise KeyError(f"Missing browser tool schema: {name}")


@dataclass(frozen=True)
class _BrowserFnSpec:
    tool_name: str
    fn: Callable[..., str]
    schema_name: str
    # Input extraction: key -> param name in tool function.
    arg_map: dict[str, str]
    # Optional positional mapping for non-schema args
    extra_params: dict[str, str] | None = None  # arg_key -> fixed param


class _SyncStringBrowserTool(BaseTool):
    """Generic wrapper for browser_utils synchronous functions."""

    def __init__(self, *, tool_info: ToolInfo, fn: Callable[..., str], arg_map: dict[str, str]) -> None:
        self._tool_info = tool_info
        self._fn = fn
        self._arg_map = arg_map

    def info(self) -> ToolInfo:
        return self._tool_info

    @property
    def requires_permission(self) -> bool:
        # Browsing is side-effect-free for local FS/repo; the command execution
        # layer already handles dangerous operations separately.
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        params = call.get_input_dict()
        try:
            kwargs: dict[str, Any] = {}
            for param_key, fn_arg in self._arg_map.items():
                if param_key in params and params[param_key] is not None:
                    kwargs[fn_arg] = params[param_key]
            # Session isolation: always pass task_id=context.session_id.
            kwargs.setdefault("task_id", context.session_id)

            # Browser tool functions are synchronous; run in thread pool.
            out = await asyncio.to_thread(self._fn, **kwargs)
            return ToolResponse(content=out)
        except Exception as e:
            return ToolResponse(
                content=json.dumps({"error": str(e)}, ensure_ascii=False),
                is_error=True,
            )


def create_browser_tools(permissions: Any = None) -> list[BaseTool]:
    """Create browser_* tools (only safe to call when requirements pass)."""
    del permissions

    tool_specs: list[_BrowserFnSpec] = [
        _BrowserFnSpec(
            tool_name="browser_navigate",
            schema_name="browser_navigate",
            fn=browser_navigate,
            arg_map={"url": "url"},
        ),
        _BrowserFnSpec(
            tool_name="browser_snapshot",
            schema_name="browser_snapshot",
            fn=browser_snapshot,
            arg_map={"full": "full"},
        ),
        _BrowserFnSpec(
            tool_name="browser_click",
            schema_name="browser_click",
            fn=browser_click,
            arg_map={"ref": "ref"},
        ),
        _BrowserFnSpec(
            tool_name="browser_type",
            schema_name="browser_type",
            fn=browser_type,
            arg_map={"ref": "ref", "text": "text"},
        ),
        _BrowserFnSpec(
            tool_name="browser_scroll",
            schema_name="browser_scroll",
            fn=browser_scroll,
            arg_map={"direction": "direction"},
        ),
        _BrowserFnSpec(
            tool_name="browser_back",
            schema_name="browser_back",
            fn=browser_back,
            arg_map={},
        ),
        _BrowserFnSpec(
            tool_name="browser_press",
            schema_name="browser_press",
            fn=browser_press,
            arg_map={"key": "key"},
        ),
        _BrowserFnSpec(
            tool_name="browser_close",
            schema_name="browser_close",
            fn=browser_close,
            arg_map={},
        ),
        _BrowserFnSpec(
            tool_name="browser_get_images",
            schema_name="browser_get_images",
            fn=browser_get_images,
            arg_map={},
        ),
        _BrowserFnSpec(
            tool_name="browser_vision",
            schema_name="browser_vision",
            fn=browser_vision,
            arg_map={"question": "question", "annotate": "annotate"},
        ),
        _BrowserFnSpec(
            tool_name="browser_console",
            schema_name="browser_console",
            fn=browser_console,
            arg_map={"clear": "clear"},
        ),
    ]

    tools: list[BaseTool] = []
    for spec in tool_specs:
        schema = _find_browser_schema(spec.schema_name)
        tool_info = _schema_to_tool_info(schema)
        tools.append(
            _SyncStringBrowserTool(
                tool_info=tool_info,
                fn=spec.fn,
                arg_map=spec.arg_map,
            )
        )
    return tools


class _SyncStringWebTool(BaseTool):
    """Generic wrapper for web_utils synchronous functions."""

    def __init__(self, *, tool_info: ToolInfo, fn: Callable[..., str], arg_map: dict[str, str]) -> None:
        self._tool_info = tool_info
        self._fn = fn
        self._arg_map = arg_map
        self._is_async = inspect.iscoroutinefunction(fn)

    def info(self) -> ToolInfo:
        return self._tool_info

    @property
    def requires_permission(self) -> bool:
        return False

    @property
    def is_dangerous(self) -> bool:
        return False

    async def run(self, call: ToolCall, context: ToolContext) -> ToolResponse:
        del context
        params = call.get_input_dict()
        try:
            kwargs: dict[str, Any] = {}
            for param_key, fn_arg in self._arg_map.items():
                if param_key in params and params[param_key] is not None:
                    kwargs[fn_arg] = params[param_key]
            if self._is_async:
                out = await self._fn(**kwargs)
            else:
                out = await asyncio.to_thread(self._fn, **kwargs)
            return ToolResponse(content=out)
        except Exception as e:
            return ToolResponse(
                content=json.dumps({"error": str(e)}, ensure_ascii=False),
                is_error=True,
            )


def create_web_tools(permissions: Any = None) -> list[BaseTool]:
    del permissions

    search_tool = _SyncStringWebTool(
        tool_info=_schema_to_tool_info(WEB_SEARCH_SCHEMA),
        fn=web_search_tool,
        arg_map={"query": "query"},
    )

    # Upstream registry schema for web_extract only requires `urls`;
    # we default to markdown extraction + LLM processing.
    async def _web_extract_wrapper(urls: list[str]) -> str:
        return await web_extract_tool(urls=urls, format="markdown")

    extract_tool = _SyncStringWebTool(
        tool_info=_schema_to_tool_info(WEB_EXTRACT_SCHEMA),
        fn=_web_extract_wrapper,
        arg_map={"urls": "urls"},
    )

    return [search_tool, extract_tool]


__all__ = ["create_browser_tools", "create_web_tools", "check_browser_requirements", "check_web_api_key"]
