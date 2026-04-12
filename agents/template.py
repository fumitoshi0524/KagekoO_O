"""Template Method runner shared by all agent modes."""

from __future__ import annotations

from dataclasses import dataclass

from core.models import AgentRequest, AgentResponse, ToolUse
from core.services import Services
from .base import Strategy


@dataclass(slots=True, kw_only=True)
class AgentRunner:
    strategy: Strategy
    services: Services

    def run(self, request: AgentRequest) -> AgentResponse:
        history = self._load_history(request)
        text, trace, tools = self._execute(request)
        self._persist(request, text)
        return AgentResponse(text=text, trace=history + trace, tools=tools)

    def _load_history(self, request: AgentRequest) -> list[str]:
        if request.session_id is None:
            return []
        return self.services.memory.read(request.session_id)

    def _execute(self, request: AgentRequest) -> tuple[str, list[str], list[ToolUse]]:
        return self.strategy.respond(request, self.services)

    def _persist(self, request: AgentRequest, response_text: str) -> None:
        if request.session_id is None:
            return
        self.services.memory.append(request.session_id, request.message)
        self.services.memory.append(request.session_id, response_text)
