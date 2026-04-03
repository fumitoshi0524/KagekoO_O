"""Rich context management for agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True, kw_only=True)
class ContextWindow:
    """Rich context container with metadata and embeddings."""

    messages: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    embeddings: list[list[float]] = field(default_factory=list)

    def add_message(self, content: str) -> None:
        self.messages.append(content)

    def add_document(self, content: str, embedding: list[float] | None = None) -> None:
        self.documents.append(content)
        if embedding is not None:
            self.embeddings.append(embedding)

    def to_prompt_context(self) -> str:
        """Serialize context for LLM prompt injection."""
        parts = []
        if self.messages:
            parts.append("## Conversation History\n" + "\n".join(self.messages))
        if self.documents:
            parts.append("## Retrieved Documents\n" + "\n".join(self.documents))
        if self.metadata:
            parts.append(
                "## Metadata\n"
                + "\n".join(f"{k}: {v}" for k, v in self.metadata.items())
            )
        return "\n\n".join(parts)
