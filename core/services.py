"""Core service container."""

from __future__ import annotations

from dataclasses import dataclass

from .ports import LLMPort, SessionStore, ToolPort, EmbeddingPort, RetrieverPort


@dataclass(slots=True, frozen=True, kw_only=True)
class Services:
    llm: LLMPort
    tools: ToolPort
    memory: SessionStore
    embedding: EmbeddingPort | None = None
    retriever: RetrieverPort | None = None
