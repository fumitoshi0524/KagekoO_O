"""Conversation memory integration."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.context import ContextWindow


@dataclass(slots=True, kw_only=True)
class InMemorySessionStore:
    _data: dict[str, list[str]] = field(default_factory=dict)
    _contexts: dict[str, ContextWindow] = field(default_factory=dict)

    def read(self, session_id: str) -> list[str]:
        return list(self._data.get(session_id, []))

    def append(self, session_id: str, item: str) -> None:
        if session_id not in self._data:
            self._data[session_id] = []
        self._data[session_id].append(item)

    def get_context(self, session_id: str) -> ContextWindow:
        """Retrieve rich context for a session."""
        if session_id not in self._contexts:
            self._contexts[session_id] = ContextWindow()
        return self._contexts[session_id]

    def update_context(self, session_id: str, context: ContextWindow) -> None:
        """Update session context with new information."""
        self._contexts[session_id] = context
