"""Agent registry — built-in agent definitions (general-purpose, explore, plan)."""

from __future__ import annotations

from dataclasses import dataclass, field

BUILTIN_AGENTS: dict[str, "AgentDefinition"] = {}


@dataclass(slots=True, kw_only=True)
class AgentDefinition:
    name: str
    description: str
    allowed_tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    read_only: bool = False
    max_turns: int = 30
    system_prompt: str = ""


class AgentRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, AgentDefinition] = dict(BUILTIN_AGENTS)

    def register(self, definition: AgentDefinition) -> None:
        self._definitions[definition.name] = definition

    def get(self, name: str) -> AgentDefinition | None:
        return self._definitions.get(name)

    def list_all(self) -> list[AgentDefinition]:
        return sorted(self._definitions.values(), key=lambda a: a.name)


# ── Built-in definitions ───────────────────────────────────────────────

BUILTIN_AGENTS["general-purpose"] = AgentDefinition(
    name="general-purpose",
    description="Universal worker agent with full tool access for complex multi-step tasks.",
    allowed_tools=["*"],
)

BUILTIN_AGENTS["explore"] = AgentDefinition(
    name="explore",
    description="Fast read-only agent for codebase exploration and search. No writes.",
    allowed_tools=["echo", "file.read", "skill.load", "skill.describe", "skill.list"],
    read_only=True,
    max_turns=15,
    system_prompt=(
        "You are a code exploration agent. Your job is to search, read, and report.\n"
        "Never modify files. Focus on finding relevant code quickly and accurately.\n"
        "Report findings concisely — what you found and where."
    ),
)

BUILTIN_AGENTS["plan"] = AgentDefinition(
    name="plan",
    description="Architecture and design agent for planning implementation approaches.",
    allowed_tools=["echo", "file.read", "skill.load", "skill.describe", "skill.list"],
    read_only=True,
    max_turns=20,
    system_prompt=(
        "You are a software architect. Design implementation plans.\n"
        "Read relevant code, identify patterns, propose approaches with trade-offs.\n"
        "Never write or execute code — only plan and analyze."
    ),
)
