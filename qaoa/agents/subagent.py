"""Sub-agent execution — fork/spawn agents reusing the QAOA engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine import QAOAEngine
    from ..adapters.tools import ToolRegistry
    from .registry import AgentDefinition


@dataclass(slots=True, kw_only=True)
class SubAgentResult:
    answer: str
    tool_calls: int = 0
    turns: int = 0
    trace: list[str] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class SubAgent:
    engine: QAOAEngine
    tools: ToolRegistry
    definition: AgentDefinition

    def run(self, query: str, skill=None) -> SubAgentResult:
        """Run sub-agent with tool filtering based on agent definition."""
        # Build filtered tool registry
        allowed = self.definition.allowed_tools
        if "*" in allowed:
            filtered_schemas = None
        else:
            all_specs = self.tools.list_specs()
            filtered = set(allowed)
            # Also filter out disallowed
            for d in self.definition.disallowed_tools:
                filtered.discard(d)
            # Filter engine's tool building (hack: temporarily override)
            original_list = self.tools.list_specs
            self.tools.list_specs = lambda: [s for s in all_specs if s.name in filtered]

        try:
            turn, trace = self.engine.run(
                query=query,
                skill=skill,
                max_turns=self.definition.max_turns,
            )
            return SubAgentResult(
                answer=turn.answer,
                tool_calls=len(turn.actions),
                turns=len([t for t in trace if "tool_calls" in t]),
                trace=trace,
            )
        finally:
            if "*" not in allowed:
                self.tools.list_specs = original_list


def run_subagent(
    engine: QAOAEngine,
    tools: ToolRegistry,
    query: str,
    agent_type: str = "general-purpose",
    skill=None,
) -> SubAgentResult:
    """Convenience function to run a sub-agent."""
    from .registry import BUILTIN_AGENTS, AgentRegistry

    registry = AgentRegistry()
    definition = registry.get(agent_type)
    if definition is None:
        definition = BUILTIN_AGENTS.get("general-purpose")

    agent = SubAgent(engine=engine, tools=tools, definition=definition)
    return agent.run(query=query, skill=skill)
