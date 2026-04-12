"""Agent-to-Agent (A2A) communication protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import AgentRequest, AgentResponse
    from core.ports import Agent


class MessageType(StrEnum):
    TASK_DELEGATION = "task_delegation"
    QUERY = "query"
    NOTIFICATION = "notification"
    RESPONSE = "response"


@dataclass(slots=True, kw_only=True)
class A2AMessage:
    """Message envelope for agent-to-agent communication."""

    sender_id: str
    recipient_id: str
    message_type: MessageType
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class AgentRegistry:
    """Registry for agent discovery and routing."""

    agents: dict[str, Agent] = field(default_factory=dict)

    def register(self, agent_id: str, agent: Agent) -> None:
        """Register an agent in the network."""
        self.agents[agent_id] = agent

    def get(self, agent_id: str) -> Agent | None:
        """Retrieve an agent by ID."""
        return self.agents.get(agent_id)

    def list_agents(self) -> list[str]:
        """List all registered agent IDs."""
        return list(self.agents.keys())


@dataclass(slots=True, kw_only=True)
class A2AOrchestrator:
    """Orchestrator for multi-agent workflows with delegation."""

    registry: AgentRegistry

    def delegate(
        self, sender_id: str, recipient_id: str, request: AgentRequest
    ) -> AgentResponse | None:
        """Delegate a task from one agent to another."""
        recipient = self.registry.get(recipient_id)
        if recipient is None:
            raise ValueError(f"Agent '{recipient_id}' not found in registry.")
        return recipient.run(request)

    def broadcast(
        self, sender_id: str, request: AgentRequest
    ) -> dict[str, AgentResponse]:
        """Broadcast a request to all agents and collect responses."""
        responses: dict[str, AgentResponse] = {}
        for agent_id, agent in self.registry.agents.items():
            if agent_id != sender_id:
                responses[agent_id] = agent.run(request)
        return responses
