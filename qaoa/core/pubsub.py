"""Lightweight pubsub broker — decouples services without heavy dependencies."""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import Any, Callable


class EventType(StrEnum):
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    SESSION_DELETED = "session.deleted"
    MESSAGE_CREATED = "message.created"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_DELETED = "message.deleted"
    SKILL_GENERATED = "skill.generated"
    SKILL_REGENERATED = "skill.regenerated"
    SKILL_ACTIVATED = "skill.activated"


Callback = Callable[[EventType, dict[str, Any]], None]


class Broker:
    """In-process pubsub broker for service decoupling."""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Callback]] = defaultdict(list)

    def subscribe(self, event: EventType, callback: Callback) -> None:
        self._subscribers[event].append(callback)

    def publish(self, event: EventType, data: dict[str, Any] | None = None) -> None:
        for cb in self._subscribers.get(event, []):
            try:
                cb(event, data or {})
            except Exception:
                pass

    def clear(self) -> None:
        self._subscribers.clear()
