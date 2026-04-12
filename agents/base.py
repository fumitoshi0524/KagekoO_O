"""Agent base protocol and shared strategy contract."""

from typing import Protocol
from abc import abstractmethod

from core.models import AgentRequest, ToolUse
from core.services import Services


class Strategy(Protocol):
    @abstractmethod
    def respond(
        self, request: AgentRequest, services: Services
    ) -> tuple[str, list[str], list[ToolUse]]:
        """Return response text, execution trace, and tool usage."""
        pass
