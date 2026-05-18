"""Plan-mode read-only policy helpers.

Parity with ClawCode clawcode/llm/plan_policy.py

This module centralizes the "planning phase is read-only" contract so both
the main Agent and subagent delegation can enforce one consistent rule-set.
"""

from __future__ import annotations

import re
from typing import Any

# Tools allowed during plan-mode research.
PLAN_ALLOWED_TOOLS = frozenset({
    "view",
    "ls",
    "glob",
    "grep",
    "diagnostics",
    "sourcegraph",
    "fetch",
    "mcp_call",
    "bash",
    "Agent",
    "Task",
    "agent",
})

# Subagent kinds considered read-only by default.
PLAN_ALLOWED_SUBAGENTS = frozenset({"plan", "explore", "code-review", "review"})

_BASH_WRITE_PATTERN = re.compile(
    r"\b("
    r"rm|mv|cp|mkdir|rmdir|touch|truncate|chmod|chown|tee|sed|awk|perl|python|node|"
    r"git\s+(add|commit|push|rebase|reset|checkout|switch|clean|apply)|"
    r"npm\s+(install|ci|update|uninstall)|"
    r"pip\s+(install|uninstall)|"
    r"cargo\s+(add|remove|install)|"
    r"go\s+(mod|get)"
    r")\b|[>|]{1,2}",
    flags=re.IGNORECASE,
)


def _bash_is_read_only(params: dict[str, Any]) -> bool:
    command = str(params.get("command") or "").strip()
    if not command:
        return False
    return _BASH_WRITE_PATTERN.search(command) is None


def is_tool_allowed_in_plan_mode(tool_name: str, params: dict[str, Any]) -> tuple[bool, str | None]:
    """Return whether this tool call is allowed during plan-mode."""
    name = (tool_name or "").strip()
    if name not in PLAN_ALLOWED_TOOLS:
        if name in {"execute_code", "cronjob"}:
            return False, f"Tool '{name}' is disabled in /plan mode (code execution / scheduling)."
        return False, f"Tool '{name}' is disabled in /plan mode."

    if name == "bash" and not _bash_is_read_only(params):
        return False, "Write-like shell command is blocked in /plan mode."

    return True, None


def filter_read_only_tools(tool_names: list[str]) -> list[str]:
    """Filter internal tool names to plan-mode safe set."""
    return [n for n in tool_names if n in PLAN_ALLOWED_TOOLS and n not in {"Agent", "Task", "agent"}]
