"""Core runtime models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AgentMode(StrEnum):
    CHAT = "chat"
    REACT = "react"
    REFLECT = "reflect"
    PLAN_EXECUTE = "plan_execute"
    RAG = "rag"
    A2A = "a2a"
    RL = "rl"


@dataclass(slots=True, kw_only=True)
class ToolUse:
    name: str
    input: str
    output: str | None = None


@dataclass(slots=True, kw_only=True)
class AgentRequest:
    message: str
    session_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    tool_plan: list[ToolUse] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class AgentResponse:
    text: str
    trace: list[str] = field(default_factory=list)
    tools: list[ToolUse] = field(default_factory=list)
