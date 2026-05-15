"""Session store with proper role-tagged messages and optional disk persistence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(slots=True, kw_only=True)
class Message:
    """A single conversation message with explicit role."""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None
    name: str | None = None  # tool name for tool role messages

    def to_dict(self) -> dict:
        d: dict = {"role": self.role, "content": self.content}
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            d["name"] = self.name
        return d

    def to_api_message(self) -> dict:
        """Convert to format compatible with LLM API calls."""
        msg: dict = {"role": self.role, "content": self.content}
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.name:
            msg["name"] = self.name
        return msg

    @classmethod
    def from_dict(cls, d: dict) -> Message:
        return cls(
            role=str(d.get("role", "user")),
            content=str(d.get("content", "")),
            tool_call_id=d.get("tool_call_id"),
            name=d.get("name"),
        )


class InMemorySessionStore:
    """In-memory session store with optional JSONL persistence.

    Supports both legacy string-based access and new Message-based access.
    """

    def __init__(self, *, persist_dir: str | Path | None = None) -> None:
        self._messages: dict[str, list[Message]] = {}
        self._legacy: dict[str, list[str]] = {}
        self._persist_dir = Path(persist_dir) if persist_dir else None
        if self._persist_dir:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._load_all()

    # ── Message-based API (preferred) ─────────────────────────────────

    def get_messages(self, session_id: str | None) -> list[Message]:
        if session_id is None:
            return []
        return list(self._messages.get(session_id, []))

    def add_message(self, session_id: str | None, message: Message) -> None:
        if session_id is None:
            return
        self._messages.setdefault(session_id, []).append(message)
        self._persist(session_id)

    def add_messages(self, session_id: str | None, messages: list[Message]) -> None:
        if session_id is None:
            return
        self._messages.setdefault(session_id, []).extend(messages)
        self._persist(session_id)

    # ── Legacy string-based API (backward compat) ─────────────────────

    def read(self, session_id: str | None) -> list[str]:
        if session_id is None:
            return []
        # Return from message store if present, else legacy
        msgs = self._messages.get(session_id)
        if msgs:
            return [m.content for m in msgs]
        return list(self._legacy.get(session_id, []))

    def append(self, session_id: str | None, content: str) -> None:
        if session_id is None:
            return
        # Auto-detect role by parity (legacy behavior)
        existing = len(self._messages.get(session_id, []))
        role = "user" if existing % 2 == 0 else "assistant"
        self.add_message(session_id, Message(role=role, content=content))

    # ── Session management ────────────────────────────────────────────

    def clear(self, session_id: str | None) -> None:
        if session_id is None:
            return
        self._messages.pop(session_id, None)
        self._legacy.pop(session_id, None)
        self._delete_persisted(session_id)

    def list_sessions(self) -> list[str]:
        all_ids = set(self._messages) | set(self._legacy)
        return sorted(all_ids)

    def resume(self, session_id: str) -> list[Message]:
        """Fully load a session's messages from disk, rebuilding if needed."""
        if session_id in self._messages:
            return list(self._messages[session_id])
        if self._persist_dir:
            path = self._persist_dir / f"{session_id}.jsonl"
            if path.exists():
                self._load_session(path)
                return list(self._messages.get(session_id, []))
        return []

    def fork(self, source_id: str, new_id: str) -> list[Message]:
        """Copy history from source session to a new session."""
        source = self.get_messages(source_id)
        if not source and self._persist_dir:
            # Try loading from disk
            path = self._persist_dir / f"{source_id}.jsonl"
            if path.exists():
                self._load_session(path)
                source = self._messages.get(source_id, [])
        if source:
            self._messages[new_id] = [Message.from_dict(m.to_dict()) for m in source]
            self._persist(new_id)
        return self._messages.get(new_id, [])

    def get_session_metadata(self, session_id: str) -> dict:
        msgs = self.get_messages(session_id)
        if not msgs:
            return {"id": session_id, "messages": 0}
        return {
            "id": session_id,
            "messages": len(msgs),
            "first_role": msgs[0].role if msgs else None,
            "last_role": msgs[-1].role if msgs else None,
        }

    def _load_session(self, path: Path) -> None:
        """Load a single session JSONL file."""
        session_id = path.stem
        messages: list[Message] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                messages.append(Message.from_dict(record))
            except (json.JSONDecodeError, TypeError):
                continue
        if messages:
            self._messages[session_id] = messages

    # ── Persistence ───────────────────────────────────────────────────

    def _persist(self, session_id: str) -> None:
        if self._persist_dir is None:
            return
        path = self._persist_dir / f"{session_id}.jsonl"
        msgs = self._messages.get(session_id, [])
        lines = [json.dumps(m.to_dict(), ensure_ascii=False) for m in msgs]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _load_all(self) -> None:
        if self._persist_dir is None:
            return
        for path in self._persist_dir.glob("*.jsonl"):
            session_id = path.stem
            messages: list[Message] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    messages.append(Message.from_dict(record))
                except (json.JSONDecodeError, TypeError):
                    continue
            if messages:
                self._messages[session_id] = messages

    def _delete_persisted(self, session_id: str) -> None:
        if self._persist_dir is None:
            return
        path = self._persist_dir / f"{session_id}.jsonl"
        if path.exists():
            path.unlink()
