"""Factory for creating agent mode implementations."""

from __future__ import annotations

from dataclasses import dataclass

from ..agents.modes import (
    ChatAgent,
    PlanExecuteAgent,
    RAGAgent,
    ReactAgent,
    ReflectAgent,
)
from .models import AgentMode
from .ports import Agent
from .services import Services


@dataclass(slots=True, kw_only=True)
class AgentFactory:
    services: Services

    def build(self, mode: AgentMode) -> Agent:
        match mode:
            case AgentMode.CHAT:
                return ChatAgent(services=self.services)
            case AgentMode.REACT:
                return ReactAgent(services=self.services)
            case AgentMode.REFLECT:
                return ReflectAgent(services=self.services)
            case AgentMode.PLAN_EXECUTE:
                return PlanExecuteAgent(services=self.services)
            case AgentMode.RAG:
                return RAGAgent(services=self.services)
            case _:
                raise ValueError(f"Unsupported agent mode: {mode}")
