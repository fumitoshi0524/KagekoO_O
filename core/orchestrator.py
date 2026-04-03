"""Facade orchestration for running agent modes."""

from __future__ import annotations

from dataclasses import dataclass

from .factory import AgentFactory
from .models import AgentMode, AgentRequest, AgentResponse


@dataclass(slots=True, kw_only=True)
class AgentOrchestrator:
    factory: AgentFactory

    def run(self, mode: AgentMode, request: AgentRequest) -> AgentResponse:
        agent = self.factory.build(mode)
        return agent.run(request)
