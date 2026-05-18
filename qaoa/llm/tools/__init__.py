"""Tool system initialization and exports.

Parity with ClawCode -- same exports: BaseTool, ToolCall, ToolContext, ToolInfo,
ToolResponse, get_builtin_tools, get_tool_schemas, find_tool, etc.
"""

from __future__ import annotations

from typing import Any

from .base import (
    BaseTool,
    ToolCall,
    ToolContext,
    ToolInfo,
    ToolResponse,
)

from .bash import create_bash_tool
from .execute_code import create_execute_code_tool
from .cronjob import create_cronjob_tool
from .process_tool import create_process_tool
from .terminal_tool import create_terminal_tool
from .file_ops import create_ls_tool, create_view_tool
from .search import create_glob_tool, create_grep_tool
from .advanced import (
    create_write_tool,
    create_edit_tool,
    create_patch_tool,
    create_fetch_tool,
    create_diagnostics_tool,
    create_mcp_tool,
    create_sourcegraph_tool,
)
from .subagent import create_agent_tool, filter_delegate_tools
from .todo import create_todo_write_tool, create_todo_read_tool, create_update_project_state_tool
from ...claw_memory.tools.memory_tool import create_memory_tool
from ...claw_skills.skill_tools import (
    create_skill_manage_tool,
    create_skills_list_tool,
    create_skill_view_tool,
)
from ...claw_search.session_search_tool import create_session_search_tool
from ...claw_learning.experience_tools import create_experience_evolve_to_skills_tool


def get_builtin_tools(
    permissions: Any = None,
    session_service: Any = None,
    message_service: Any = None,
    lsp_clients: Any = None,
    lsp_manager: Any = None,
    plugin_manager: Any = None,
    for_kageko_mode: bool | None = None,
) -> list[BaseTool]:
    """Get all built-in tools.

    Args:
        permissions: Permission service (optional)
        session_service: Session service (optional)
        message_service: Message service (optional)
        lsp_clients: LSP clients (optional)
        lsp_manager: LSP manager (optional)
        plugin_manager: PluginManager instance (optional)
        for_kageko_mode: When ``desktop.tools_require_kageko_mode`` is set, pass ``False`` to omit
            ``desktop_*`` tools (TUI default path). ``None`` keeps legacy behavior (CLI).

    Returns:
        List of tool instances
    """
    hook_engine = getattr(plugin_manager, "hook_engine", None) if plugin_manager else None

    # Map config reference names for clarity
    _kageko_config_names = {
        "tools_require_kageko_mode": "tools_require_kageko_mode",
    }

    tools: list[BaseTool] = [
        # Basic tools
        create_bash_tool(permissions),
        create_execute_code_tool(permissions),
        create_process_tool(permissions),
        create_terminal_tool(permissions),
        create_view_tool(permissions),
        create_ls_tool(permissions),
        create_glob_tool(permissions),
        create_grep_tool(permissions),
        create_cronjob_tool(permissions),
        # Advanced tools
        create_write_tool(permissions),
        create_edit_tool(permissions),
        create_patch_tool(permissions),
        create_fetch_tool(permissions),
        # LSP tools
        create_diagnostics_tool(permissions, lsp_manager),
        # Task management tools
        create_todo_write_tool(permissions),
        create_todo_read_tool(permissions),
        create_update_project_state_tool(permissions),
        # Kageko closed-loop learning tools
        create_memory_tool(permissions),
        create_skills_list_tool(),
        create_skill_view_tool(),
        create_skill_manage_tool(),
        create_experience_evolve_to_skills_tool(),
        create_session_search_tool(session_service=session_service, message_service=message_service),
    ]
    # Sub-agent tool: sub-agents must not hold Agent/Task to avoid nested delegation
    tools.append(
        create_agent_tool(
            permissions=permissions,
            session_service=session_service,
            message_service=message_service,
            hook_engine=hook_engine,
            provider=None,
            available_tools=filter_delegate_tools(list(tools)),
        )
    )

    # Merge plugin MCP servers into settings before checking.
    if plugin_manager is not None:
        try:
            plugin_mcp = plugin_manager.get_merged_mcp_servers()
            if plugin_mcp:
                from ..config import get_settings as _gs
                _settings = _gs()
                for k, v in plugin_mcp.items():
                    if k not in _settings.mcp_servers:
                        _settings.mcp_servers[k] = v
        except Exception:
            pass

    # MCP tools (only meaningful when MCP servers are configured)
    try:
        from ..config import get_settings

        settings = get_settings()
        if settings.mcp_servers:
            tools.append(create_mcp_tool(permissions))
        # Sourcegraph tools (only registered when enabled and url is set)
        if getattr(settings, "sourcegraph", None) and getattr(
            settings.sourcegraph, "enabled", False
        ):
            url = getattr(settings.sourcegraph, "url", "").strip()
            if url:
                token = getattr(settings.sourcegraph, "access_token", None)
                tools.append(
                    create_sourcegraph_tool(
                        base_url=url,
                        access_token=token,
                        permissions=permissions,
                    )
                )
    except Exception:
        # If settings haven't loaded yet or another issue, skip MCP / Sourcegraph tools
        pass

    # Browser / Web tools (optional)
    try:
        from .browser.browser_tools import (
            check_browser_requirements,
            check_web_api_key,
            create_browser_tools,
            create_web_tools,
        )

        if check_browser_requirements():
            tools.extend(create_browser_tools(permissions))

        # Web tools are cheap schema-wise and fail gracefully at runtime
        # when no backend API keys are configured.
        tools.extend(create_web_tools(permissions))
    except Exception:
        # Browser/Web tools are best-effort; never break core tool loading.
        pass

    # Desktop / Computer Use tools (optional: settings + mss + pyautogui)
    try:
        from .desktop.desktop_tools import create_desktop_tools
        from .desktop.desktop_utils import check_desktop_requirements

        if check_desktop_requirements(for_kageko_mode=for_kageko_mode):
            tools.extend(create_desktop_tools(permissions))
    except Exception:
        pass

    return tools


def get_tool_schemas(tools: list[BaseTool]) -> list[dict[str, Any]]:
    """Get all tool schemas for LLM.

    Args:
        tools: List of tools

    Returns:
        List of tool schema dictionaries
    """
    schemas = []
    for tool in tools:
        info = tool.info()
        schemas.append(info.to_dict())
    return schemas


def find_tool(tools: list[BaseTool], name: str) -> BaseTool | None:
    """Find a tool by name.

    Args:
        tools: List of tools
        name: Tool name

    Returns:
        Tool or None if not found
    """
    for tool in tools:
        if tool.info().name == name:
            return tool
    if name in ("Task", "agent"):
        for tool in tools:
            if tool.info().name == "Agent":
                return tool
    return None


from .subagent import (
    SubAgent,
    SubAgentContext,
    SubAgentResult,
    SubAgentType,
    IsolationMode,
)

from .adapter import (
    LogicalToolOp,
    ToolAdapter,
    create_tool_adapter_from_builtin,
)

__all__ = [
    "BaseTool",
    "ToolCall",
    "ToolContext",
    "ToolInfo",
    "ToolResponse",
    "get_builtin_tools",
    "get_tool_schemas",
    "find_tool",
    "create_diagnostics_tool",
    # Subagent exports
    "SubAgent",
    "SubAgentContext",
    "SubAgentResult",
    "SubAgentType",
    "IsolationMode",
    # Programmatic tool adapter (logical op -> BaseTool)
    "LogicalToolOp",
    "ToolAdapter",
    "create_tool_adapter_from_builtin",
]
