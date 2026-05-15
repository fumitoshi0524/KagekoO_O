"""Sub-agent system — fork/spawn agents reusing the QAOA engine."""

from __future__ import annotations

from .subagent import SubAgent, run_subagent
from .registry import AgentRegistry, BUILTIN_AGENTS

__all__ = [
    "SubAgent",
    "run_subagent",
    "AgentRegistry",
    "BUILTIN_AGENTS",
]
