# QAOA category: operations, domain: technology
"""Tool adapter layer -- unified programmatic invocation over built-in tools.

Parity with ClawCode -- same LogicalToolOp enum, ToolAdapter class,
_NORMALIZERS mapping, create_tool_adapter_from_builtin.

Upper layers pass a **logical operation name** and a parameter dict; this module
maps to the concrete ``BaseTool`` name, normalizes aliases (e.g. ``path`` ->
``file_path`` for ``view``), builds a ``ToolCall``, and runs ``run`` or
aggregates ``run_stream`` into a single ``ToolResponse``.

Logical op -> real tool name
----------------------------
``read_file``              -> ``view``
``list_dir``               -> ``ls``
``find_files``             -> ``glob``
``search_content``         -> ``grep``
``write_file``             -> ``write``
``edit_file``              -> ``edit``
``apply_patch``            -> ``patch``
``http_fetch``             -> ``fetch``
``shell``                  -> ``bash``
``todo_write``             -> ``TodoWrite``
``todo_read``              -> ``TodoRead``
``update_project_state``   -> ``UpdateProjectState``
``lsp_diagnostics``        -> ``diagnostics``
``mcp``                    -> ``mcp_call``
``code_search_sg``         -> ``sourcegraph`` (only if that tool is registered)

**Not supported** (intentional): ``Agent`` / ``Task`` / subagent delegation --
use the agent API directly to avoid accidental nested runs.

This module does **not** register any extra LLM-visible tools; existing
``get_builtin_tools`` and ``Agent`` behavior stay unchanged.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Callable

from .base import BaseTool, ToolCall, ToolContext, ToolResponse


class LogicalToolOp(StrEnum):
    """Stable logical names for ``ToolAdapter.invoke``."""

    READ_FILE = "read_file"
    LIST_DIR = "list_dir"
    FIND_FILES = "find_files"
    SEARCH_CONTENT = "search_content"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    APPLY_PATCH = "apply_patch"
    HTTP_FETCH = "http_fetch"
    SHELL = "shell"
    TODO_WRITE = "todo_write"
    TODO_READ = "todo_read"
    UPDATE_PROJECT_STATE = "update_project_state"
    LSP_DIAGNOSTICS = "lsp_diagnostics"
    MCP = "mcp"
    CODE_SEARCH_SG = "code_search_sg"


# Subagent / delegation not exposed through the adapter.
_FORBIDDEN_OPS = frozenset(
    {
        "agent",
        "task",
        "subagent",
        "invoke_subagent",
        "delegate",
    }
)

# logical_op (str) -> concrete tool name
_OP_TO_TOOL: dict[str, str] = {
    "read_file": "view",
    "list_dir": "ls",
    "find_files": "glob",
    "search_content": "grep",
    "write_file": "write",
    "edit_file": "edit",
    "apply_patch": "patch",
    "http_fetch": "fetch",
    "shell": "bash",
    "todo_write": "TodoWrite",
    "todo_read": "TodoRead",
    "update_project_state": "UpdateProjectState",
    "lsp_diagnostics": "diagnostics",
    "mcp": "mcp_call",
    "code_search_sg": "sourcegraph",
}


def _pick_path(params: dict[str, Any]) -> str:
    for key in ("file_path", "filePath", "path", "filename"):
        v = params.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _normalize_read_file(params: dict[str, Any]) -> dict[str, Any]:
    fp = _pick_path(params)
    out: dict[str, Any] = {"file_path": fp}
    if "offset" in params:
        out["offset"] = params["offset"]
    if "limit" in params:
        out["limit"] = params["limit"]
    return out


def _normalize_list_dir(params: dict[str, Any]) -> dict[str, Any]:
    p = params.get("path") or params.get("directory") or "."
    out: dict[str, Any] = {"path": p if isinstance(p, str) else str(p)}
    if "recursive" in params:
        out["recursive"] = bool(params["recursive"])
    return out


def _normalize_find_files(params: dict[str, Any]) -> dict[str, Any]:
    pat = params.get("pattern") or params.get("glob") or ""
    out: dict[str, Any] = {"pattern": pat if isinstance(pat, str) else str(pat)}
    if "path" in params:
        out["path"] = params["path"]
    return out


def _normalize_search_content(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "pattern" in params:
        out["pattern"] = params["pattern"]
    if "path" in params:
        out["path"] = params["path"]
    if "file_pattern" in params:
        out["file_pattern"] = params["file_pattern"]
    if "case_insensitive" in params:
        out["case_insensitive"] = params["case_insensitive"]
    if "context_lines" in params:
        out["context_lines"] = params["context_lines"]
    return out


def _normalize_write_file(params: dict[str, Any]) -> dict[str, Any]:
    fp = _pick_path(params)
    content = params.get("content")
    if content is None and "text" in params:
        content = params["text"]
    out: dict[str, Any] = {"file_path": fp, "content": content if content is not None else ""}
    if "create_dirs" in params:
        out["create_dirs"] = params["create_dirs"]
    return out


def _normalize_edit_file(params: dict[str, Any]) -> dict[str, Any]:
    fp = _pick_path(params)
    out: dict[str, Any] = {"file_path": fp, "replacements": params.get("replacements", [])}
    return out


def _normalize_apply_patch(params: dict[str, Any]) -> dict[str, Any]:
    fp = _pick_path(params)
    patch = params.get("patch") or params.get("diff") or ""
    return {"file_path": fp, "patch": patch if isinstance(patch, str) else str(patch)}


def _normalize_http_fetch(params: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in params.items() if k in ("url", "method", "headers", "body", "max_size")}
    return out


def _normalize_shell(params: dict[str, Any]) -> dict[str, Any]:
    cmd = params.get("command") or params.get("cmd") or ""
    out: dict[str, Any] = {"command": cmd if isinstance(cmd, str) else str(cmd)}
    if "cwd" in params:
        out["cwd"] = params["cwd"]
    if "timeout" in params:
        out["timeout"] = params["timeout"]
    return out


def _normalize_todo_write(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"todos": params.get("todos", [])}
    if "merge" in params:
        out["merge"] = params["merge"]
    return out


def _normalize_todo_read(_params: dict[str, Any]) -> dict[str, Any]:
    return {}


def _normalize_update_project_state(params: dict[str, Any]) -> dict[str, Any]:
    c = params.get("content") or params.get("markdown") or ""
    return {"content": c if isinstance(c, str) else str(c)}


def _normalize_lsp_diagnostics(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    fp = params.get("file_path") or params.get("path")
    if fp:
        out["file_path"] = fp
    if "severity" in params:
        out["severity"] = params["severity"]
    return out


def _normalize_mcp(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "server" in params:
        out["server"] = params["server"]
    if "tool" in params:
        out["tool"] = params["tool"]
    if "arguments" in params:
        out["arguments"] = params["arguments"]
    if "list_only" in params:
        out["list_only"] = params["list_only"]
    return out


def _normalize_code_search_sg(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "query" in params:
        out["query"] = params["query"]
    if "repo" in params:
        out["repo"] = params["repo"]
    if "path" in params:
        out["path"] = params["path"]
    if "limit" in params:
        out["limit"] = params["limit"]
    return out


_NORMALIZERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "read_file": _normalize_read_file,
    "list_dir": _normalize_list_dir,
    "find_files": _normalize_find_files,
    "search_content": _normalize_search_content,
    "write_file": _normalize_write_file,
    "edit_file": _normalize_edit_file,
    "apply_patch": _normalize_apply_patch,
    "http_fetch": _normalize_http_fetch,
    "shell": _normalize_shell,
    "todo_write": _normalize_todo_write,
    "todo_read": _normalize_todo_read,
    "update_project_state": _normalize_update_project_state,
    "lsp_diagnostics": _normalize_lsp_diagnostics,
    "mcp": _normalize_mcp,
    "code_search_sg": _normalize_code_search_sg,
}


def _canonical_op(op: str | LogicalToolOp) -> str:
    s = str(op or "").strip().lower().replace("-", "_")
    return s


class ToolAdapter:
    """Maps logical operations to registered ``BaseTool`` instances and runs them."""

    def __init__(self, tools: list[BaseTool]) -> None:
        _seen: set[int] = set()
        unique: list[BaseTool] = []
        for t in tools:
            tid = id(t)
            if tid in _seen:
                continue
            _seen.add(tid)
            unique.append(t)

        self._tools: dict[str, BaseTool] = {t.info().name: t for t in unique}
        if "Agent" in self._tools:
            self._tools["Task"] = self._tools["Agent"]

    def _get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def has_logical_op(self, op: str) -> bool:
        """Return True if *op* is a known logical operation."""
        key = _canonical_op(op)
        return key in _OP_TO_TOOL

    def list_logical_ops(self) -> list[str]:
        """Return logical operation names (enum order)."""
        return [e.value for e in LogicalToolOp]

    async def invoke(
        self,
        op: str,
        params: dict[str, Any],
        context: ToolContext,
        *,
        tool_call_id: str | None = None,
    ) -> ToolResponse:
        """Run the tool for logical operation *op* with normalized *params*."""
        key = _canonical_op(op)
        if key in _FORBIDDEN_OPS:
            return ToolResponse.error(
                f"Logical op '{op}' is not supported via ToolAdapter (use the agent API for delegation)."
            )

        tool_name = _OP_TO_TOOL.get(key)
        if not tool_name:
            return ToolResponse.error(f"Unknown logical tool op: {op}")

        normalizer = _NORMALIZERS.get(key)
        if not normalizer:
            return ToolResponse.error(f"No normalizer registered for op: {op}")

        normalized = normalizer(dict(params))
        tool = self._get_tool(tool_name)
        if tool is None:
            return ToolResponse.error(
                f"Tool '{tool_name}' is not available in this adapter (not registered)."
            )

        call_id = tool_call_id or f"adapter-{uuid.uuid4().hex[:12]}"
        call = ToolCall(id=call_id, name=tool_name, input=normalized)

        run_stream = getattr(tool, "run_stream", None)
        if callable(run_stream):
            final: ToolResponse | None = None
            async for partial in run_stream(call, context):  # type: ignore[misc]
                meta = (partial.metadata or "").lower()
                if meta.startswith("final"):
                    final = partial
                    break
            if final is None:
                final = await tool.run(call, context)
            return final

        return await tool.run(call, context)


def create_tool_adapter_from_builtin(
    permissions: Any = None,
    session_service: Any = None,
    message_service: Any = None,
    lsp_clients: Any = None,
    lsp_manager: Any = None,
    plugin_manager: Any = None,
) -> ToolAdapter:
    """Build a ``ToolAdapter`` around ``get_builtin_tools`` with the same kwargs as callers."""
    from . import get_builtin_tools

    tools = get_builtin_tools(
        permissions=permissions,
        session_service=session_service,
        message_service=message_service,
        lsp_clients=lsp_clients,
        lsp_manager=lsp_manager,
        plugin_manager=plugin_manager,
    )
    return ToolAdapter(tools)
