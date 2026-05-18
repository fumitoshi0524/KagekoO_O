"""Deprecated import path; use qaoa.llm.tools.subagent instead.

Parity with ClawCode clawcode/llm/subagent.py
"""

from .tools.subagent import (
    AgentTool,
    IsolationMode,
    SubAgent,
    SubAgentContext,
    SubAgentEventType,
    SubAgentResult,
    SubAgentType,
    create_agent_tool,
    create_subagent_tool,
)

__all__ = [
    "SubAgent",
    "SubAgentContext",
    "SubAgentResult",
    "SubAgentType",
    "SubAgentEventType",
    "IsolationMode",
    "AgentTool",
    "create_agent_tool",
    "create_subagent_tool",
]
