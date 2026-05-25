# src/kageko/types.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentMode(str, Enum):
    TOOL_USE = "tool-use"
    QAOA = "qaoa"


@dataclass
class Message:
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": self.args},
        }


@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False

    def to_message(self) -> Message:
        return Message(
            role="tool",
            content=self.content,
            tool_call_id=self.tool_call_id,
        )


@dataclass
class AgentResult:
    answer: str
    turn_count: int = 0
    tokens_used: int = 0
    trajectory: Any = None  # QAOATrajectory | None


@dataclass
class QAOAStep:
    """Single step in QAOA trajectory: Action + Observation."""
    step_number: int
    action: ToolCall
    observation: ToolResult


@dataclass
class QAOATrajectory:
    """Full QAOA trajectory for research/export."""
    query: str
    steps: list[QAOAStep] = field(default_factory=list)
    answer: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def step(self, action: ToolCall, observation: ToolResult) -> None:
        self.steps.append(QAOAStep(
            step_number=len(self.steps) + 1,
            action=action,
            observation=observation,
        ))

    def set_answer(self, answer: str) -> None:
        self.answer = answer
