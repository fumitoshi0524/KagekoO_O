"""Message handling — ClawCode pattern with content parts."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from ..core.pubsub import Broker, EventType
from ..db.connection import Database


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass(slots=True, kw_only=True)
class ContentPart:
    type: str
    content: str = ""

    def to_dict(self) -> dict:
        return {"type": self.type, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> ContentPart:
        return cls(type=data.get("type", "text"), content=data.get("content", ""))

    @classmethod
    def text(cls, content: str) -> ContentPart:
        return cls(type="text", content=content)

    @classmethod
    def tool_call(cls, name: str, input_str: str, call_id: str = "") -> ContentPart:
        return cls(type="tool_call", content=f"{name}:{input_str}" if not call_id else f"{call_id}:{name}:{input_str}")

    @classmethod
    def tool_result(cls, call_id: str, content: str, is_error: bool = False) -> ContentPart:
        prefix = "error:" if is_error else "result:"
        return cls(type="tool_result", content=f"{call_id}:{prefix}{content}")

    @classmethod
    def thinking(cls, content: str) -> ContentPart:
        return cls(type="thinking", content=content)


@dataclass(slots=True, kw_only=True)
class Message:
    id: str
    session_id: str
    role: MessageRole
    parts: list[ContentPart] = field(default_factory=list)
    model: str = ""
    created_at: float = field(default_factory=time.time)
    deleted_at: float | None = None

    @property
    def content(self) -> str:
        texts = [p.content for p in self.parts if p.type == "text"]
        return "\n".join(texts)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class MessageService:
    """CRUD for messages with content parts and pubsub."""

    def __init__(self, db: Database, broker: Broker | None = None) -> None:
        self._db = db
        self._broker = broker or Broker()

    def create(self, session_id: str, role: MessageRole, content: str = "",
               *, parts: list[ContentPart] | None = None, model: str = "") -> Message:
        msg = Message(
            id=uuid.uuid4().hex[:12],
            session_id=session_id,
            role=role,
            parts=parts or ([ContentPart.text(content)] if content else []),
            model=model,
        )
        self._db.append("messages", {
            "id": msg.id, "session_id": msg.session_id,
            "role": str(msg.role),
            "parts": [p.to_dict() for p in msg.parts],
            "model": msg.model, "created_at": msg.created_at,
            "deleted_at": msg.deleted_at,
        })
        self._broker.publish(EventType.MESSAGE_CREATED, {"id": msg.id, "session_id": session_id})
        return msg

    def get(self, message_id: str) -> Message | None:
        records = self._db.read_where("messages", key="id", value=message_id)
        if not records:
            return None
        msg = self._from_dict(records[0])
        return None if msg.is_deleted else msg

    def list_by_session(self, session_id: str, limit: int = 100) -> list[Message]:
        records = self._db.read_where("messages", key="session_id", value=session_id)
        messages = [self._from_dict(r) for r in records if not r.get("deleted_at")]
        messages.sort(key=lambda m: m.created_at)
        return messages[-limit:]

    def update(self, message: Message) -> None:
        self._db.update_where("messages", key="id", value=message.id, updates={
            "parts": [p.to_dict() for p in message.parts],
            "deleted_at": message.deleted_at,
        })
        self._broker.publish(EventType.MESSAGE_UPDATED, {"id": message.id})

    def soft_delete(self, message_id: str) -> None:
        self._db.update_where("messages", key="id", value=message_id,
                              updates={"deleted_at": time.time()})
        self._broker.publish(EventType.MESSAGE_DELETED, {"id": message_id})

    @staticmethod
    def _from_dict(data: dict) -> Message:
        parts_raw = data.get("parts", [])
        parts = [ContentPart.from_dict(p) for p in parts_raw] if isinstance(parts_raw, list) else []
        return Message(
            id=data["id"], session_id=data.get("session_id", ""),
            role=MessageRole(data.get("role", "user")),
            parts=parts,
            model=data.get("model", ""),
            created_at=data.get("created_at", 0.0),
            deleted_at=data.get("deleted_at"),
        )
