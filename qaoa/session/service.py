"""Session management — ClawCode pattern with JSONL persistence and pubsub."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..core.pubsub import Broker, EventType
from ..db.connection import Database


@dataclass(slots=True, kw_only=True)
class Session:
    id: str
    title: str = ""
    message_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    parent_session_id: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class SessionService:
    """CRUD for sessions with pubsub notifications."""

    def __init__(self, db: Database, broker: Broker | None = None) -> None:
        self._db = db
        self._broker = broker or Broker()

    def create(self, *, title: str = "", parent_session_id: str | None = None) -> Session:
        session = Session(
            id=uuid.uuid4().hex[:12],
            title=title or f"Chat {int(time.time())}",
            parent_session_id=parent_session_id,
        )
        self._db.append("sessions", {
            "id": session.id, "title": session.title,
            "message_count": session.message_count,
            "prompt_tokens": session.prompt_tokens,
            "completion_tokens": session.completion_tokens,
            "cost": session.cost,
            "parent_session_id": session.parent_session_id,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        })
        self._broker.publish(EventType.SESSION_CREATED, {"id": session.id})
        return session

    def get(self, session_id: str) -> Session | None:
        records = self._db.read_where("sessions", key="id", value=session_id)
        if not records:
            return None
        return self._from_dict(records[0])

    def list(self, limit: int = 50, parent_session_id: str | None = None) -> list[Session]:
        records = self._db.read_all("sessions")
        if parent_session_id:
            records = [r for r in records if r.get("parent_session_id") == parent_session_id]
        records.sort(key=lambda r: r.get("updated_at", 0), reverse=True)
        return [self._from_dict(r) for r in records[:limit]]

    def update(self, session: Session) -> None:
        session.updated_at = time.time()
        self._db.update_where("sessions", key="id", value=session.id, updates={
            "title": session.title, "message_count": session.message_count,
            "prompt_tokens": session.prompt_tokens,
            "completion_tokens": session.completion_tokens,
            "cost": session.cost, "updated_at": session.updated_at,
        })
        self._broker.publish(EventType.SESSION_UPDATED, {"id": session.id})

    def delete(self, session_id: str) -> None:
        self._db.delete_where("sessions", key="id", value=session_id)
        self._broker.publish(EventType.SESSION_DELETED, {"id": session_id})

    def increment_message_count(self, session_id: str) -> None:
        session = self.get(session_id)
        if session:
            session.message_count += 1
            self.update(session)

    def add_token_usage(self, session_id: str, prompt: int, completion: int, cost: float = 0.0) -> None:
        session = self.get(session_id)
        if session:
            session.prompt_tokens += prompt
            session.completion_tokens += completion
            session.cost += cost
            self.update(session)

    def subscribe(self, callback) -> None:
        for event in EventType:
            if event.value.startswith("session."):
                self._broker.subscribe(event, callback)

    @staticmethod
    def _from_dict(data: dict) -> Session:
        return Session(
            id=data["id"], title=data.get("title", ""),
            message_count=data.get("message_count", 0),
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            cost=data.get("cost", 0.0),
            parent_session_id=data.get("parent_session_id"),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )
