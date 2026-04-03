"""Concrete agent modes."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.models import AgentRequest, AgentResponse
from ..core.services import Services
from .strategies import (
    ChatStrategy,
    PlanExecuteStrategy,
    RAGStrategy,
    ReactStrategy,
    ReflectStrategy,
)
from .template import AgentRunner


@dataclass(slots=True, kw_only=True)
class ChatAgent:
    services: Services

    def run(self, request: AgentRequest) -> AgentResponse:
        return AgentRunner(strategy=ChatStrategy(), services=self.services).run(request)


@dataclass(slots=True, kw_only=True)
class ReactAgent:
    services: Services

    def run(self, request: AgentRequest) -> AgentResponse:
        return AgentRunner(strategy=ReactStrategy(), services=self.services).run(
            request
        )


@dataclass(slots=True, kw_only=True)
class ReflectAgent:
    services: Services

    def run(self, request: AgentRequest) -> AgentResponse:
        return AgentRunner(strategy=ReflectStrategy(), services=self.services).run(
            request
        )


@dataclass(slots=True, kw_only=True)
class PlanExecuteAgent:
    services: Services

    def run(self, request: AgentRequest) -> AgentResponse:
        return AgentRunner(strategy=PlanExecuteStrategy(), services=self.services).run(
            request
        )


@dataclass(slots=True, kw_only=True)
class RAGAgent:
    services: Services

    def run(self, request: AgentRequest) -> AgentResponse:
        if self.services.retriever is None:
            raise ValueError("RAG mode requires a configured retriever.")
        return AgentRunner(
            strategy=RAGStrategy(self.services.retriever), services=self.services
        ).run(request)
