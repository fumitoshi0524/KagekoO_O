"""Core runtime models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

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


# ── Tool types (execution primitives behind skills) ──────────────────

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


# ── QAOA Skill (legacy, kept for backward compat) ────────────────────

@dataclass(slots=True, kw_only=True)
class QAOASkill:
    name: str
    objective: str
    tools: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)


# ── Skill System (primary abstraction) ───────────────────────────────

@dataclass(slots=True, kw_only=True)
class SkillSpec:
    """Kageko-native skill — the primary agent abstraction.

    Superset of Claude Code's markdown+YAML frontmatter format.
    """
    name: str
    description: str
    instructions: str
    allowed_tools: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None
    format: str = "kageko-native"


@dataclass(slots=True, kw_only=True)
class SkillAction:
    """An action taken during skill execution."""
    skill_name: str
    action_type: str  # "tool_call" | "think" | "respond" | "ask_user"
    tool_name: str | None = None
    tool_input: str | None = None


@dataclass(slots=True, kw_only=True)
class UserPermission:
    """Permission request for a risky operation."""
    skill_name: str
    tool_name: str
    risk_level: str
    description: str
    granted: bool = False


def skill_from_qaoa(qaoa_skill: QAOASkill, /) -> SkillSpec:
    """Convert a legacy QAOASkill to the new SkillSpec format."""
    if qaoa_skill.steps:
        steps_text = "\n".join(f"{i}. {s}" for i, s in enumerate(qaoa_skill.steps, 1))
        instructions = f"Objective: {qaoa_skill.objective}\n\nSteps:\n{steps_text}"
    else:
        instructions = f"Objective: {qaoa_skill.objective}"
    return SkillSpec(
        name=qaoa_skill.name,
        description=qaoa_skill.objective,
        instructions=instructions,
        allowed_tools=list(qaoa_skill.tools),
        format="qaoa-legacy",
    )


# ── Conformance & Evaluation types ────────────────────────────────────

@dataclass(slots=True, frozen=True, kw_only=True)
class ConformanceResult:
    """Result of skill conformance validation against UniToolCall standard."""
    passed: bool
    reason: str = ""
    issues: list[str] = field(default_factory=list)
    score: float = 0.0  # 0.0–1.0 conformance score


@dataclass(slots=True, frozen=True, kw_only=True)
class EvalScore:
    """Evaluation scores for a skill against benchmark queries."""
    toolfit: float       # how well tools match the query domain
    clarity: float       # how clear the instruction steps are
    naturalness: float   # how natural the QAOA flow is

    @property
    def average(self) -> float:
        return (self.toolfit + self.clarity + self.naturalness) / 3.0

    def passes(self, threshold: float = 7.0) -> bool:
        return self.average >= threshold


@dataclass(slots=True, frozen=True, kw_only=True)
class RegenerationFeedback:
    """Feedback from evaluation to drive skill regeneration."""
    query: str
    expected_tools: list[str]
    observed_tools: list[str]
    eval_score: EvalScore
    suggestions: str = ""


# ── QAOA Turn types ──────────────────────────────────────────────────

@dataclass(slots=True, kw_only=True)
class QAOATurn:
    query: str
    skill: SkillSpec | QAOASkill | None = None
    actions: list[QAOAAction] = field(default_factory=list)
    observations: list[QAOAObservation] = field(default_factory=list)
    answer: str = ""


# ── Request / Response ───────────────────────────────────────────────

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
