"""Core runtime models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# UniToolCall functional categories (arXiv:2604.11557 Section 3.1)
FUNCTIONAL_CATEGORIES: tuple[str, ...] = (
    "analysis",
    "operations",
    "system",
    "visualization",
    "search",
    "generate",
)

# UniToolCall application domains
APPLICATION_DOMAINS: tuple[str, ...] = (
    "finance",
    "technology",
    "education",
    "healthcare",
    "entertainment",
    "travel",
    "business",
    "lifestyle",
    "science",
    "social",
    "sports",
    "environment",
    "culture",
)


class AgentMode(StrEnum):
    QAOA = "qaoa"


@dataclass(slots=True, kw_only=True)
class ToolUse:
    name: str
    input: str
    output: str | None = None


@dataclass(slots=True, kw_only=True)
class QAOAAction:
    name: str
    input: str


@dataclass(slots=True, kw_only=True)
class QAOAObservation:
    action_name: str
    output: str


@dataclass(slots=True, kw_only=True)
class QAOASkill:
    name: str
    objective: str
    tools: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class QAOATurn:
    query: str
    skill: QAOASkill | None = None
    actions: list[QAOAAction] = field(default_factory=list)
    observations: list[QAOAObservation] = field(default_factory=list)
    answer: str = ""


@dataclass(slots=True, kw_only=True)
class AgentRequest:
    message: str
    session_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    tool_plan: list[ToolUse] = field(default_factory=list)

    @property
    def query(self) -> str:
        return self.message


@dataclass(slots=True, kw_only=True)
class AgentResponse:
    answer: str
    trace: list[str] = field(default_factory=list)
    qaoa_turns: list[QAOATurn] = field(default_factory=list)
    tools: list[ToolUse] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.answer
