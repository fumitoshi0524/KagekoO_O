"""Core ports for adapters."""

from __future__ import annotations

from typing import Protocol
from abc import abstractmethod

from .models import AgentRequest, AgentResponse
from .context import ContextWindow


class LLMPort(Protocol):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Generate response text."""


class ToolPort(Protocol):
    @abstractmethod
    def call(self, name: str, payload: str) -> str:
        """Call a named tool."""


class SessionStore(Protocol):
    @abstractmethod
    def read(self, session_id: str) -> list[str]:
        """Read conversation history for a session."""

    @abstractmethod
    def append(self, session_id: str, item: str) -> None:
        """Append one entry to session history."""

    @abstractmethod
    def get_context(self, session_id: str) -> ContextWindow:
        """Retrieve rich context for a session."""

    @abstractmethod
    def update_context(self, session_id: str, context: ContextWindow) -> None:
        """Update session context with new information."""


class Agent(Protocol):
    @abstractmethod
    def run(self, request: AgentRequest) -> AgentResponse:
        """Execute an agent for one request."""


class EmbeddingPort(Protocol):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""


class RetrieverPort(Protocol):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        """Retrieve relevant documents for query."""

    @abstractmethod
    def add_documents(self, documents: list[str]) -> None:
        """Add documents to retrieval corpus."""
