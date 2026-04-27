"""Session store with optional disk persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class InMemorySessionStore:
    """In-memory session store with optional JSONL persistence."""

    def __init__(self, *, persist_dir: str | Path | None = None) -> None:
        self._sessions: dict[str, list[str]] = {}
        self._persist_dir = Path(persist_dir) if persist_dir else None
        if self._persist_dir:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._load_all()

    def read(self, session_id: str | None) -> list[str]:
        if session_id is None:
            return []
        return list(self._sessions.get(session_id, []))

    def append(self, session_id: str | None, message: str) -> None:
        if session_id is None:
            return
        self._sessions.setdefault(session_id, []).append(message)
        self._persist_session(session_id)

    def clear(self, session_id: str | None) -> None:
        if session_id is None:
            return
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._delete_persisted(session_id)

    def list_sessions(self) -> list[str]:
        return sorted(self._sessions)

    def _persist_session(self, session_id: str) -> None:
        if self._persist_dir is None:
            return
        path = self._persist_dir / f"{session_id}.jsonl"
        lines = [{"role": "user" if i % 2 == 0 else "assistant", "content": msg} for i, msg in enumerate(self._sessions[session_id])]
        path.write_text("\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + "\n", encoding="utf-8")

    def _load_all(self) -> None:
        if self._persist_dir is None:
            return
        for path in self._persist_dir.glob("*.jsonl"):
            session_id = path.stem
            messages: list[str] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    messages.append(str(record.get("content", "")))
                except json.JSONDecodeError:
                    continue
            if messages:
                self._sessions[session_id] = messages

    def _delete_persisted(self, session_id: str) -> None:
        if self._persist_dir is None:
            return
        path = self._persist_dir / f"{session_id}.jsonl"
        if path.exists():
            path.unlink()
