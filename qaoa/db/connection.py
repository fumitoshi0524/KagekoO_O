"""Lightweight JSONL database — no SQLAlchemy dependency."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any


class Database:
    """JSONL-based persistence for sessions and messages."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, Lock] = {}

    def _lock(self, name: str) -> Lock:
        if name not in self._locks:
            self._locks[name] = Lock()
        return self._locks[name]

    @contextmanager
    def session(self, name: str):
        """Context manager for atomic operations on a named JSONL file."""
        lock = self._lock(name)
        with lock:
            yield self

    def append(self, name: str, record: dict[str, Any]) -> None:
        path = self.data_dir / f"{name}.jsonl"
        with self._lock(name):
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_all(self, name: str) -> list[dict[str, Any]]:
        path = self.data_dir / f"{name}.jsonl"
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError:
                pass
        return records

    def read_where(self, name: str, *, key: str, value: Any) -> list[dict[str, Any]]:
        return [r for r in self.read_all(name) if r.get(key) == value]

    def update_where(self, name: str, *, key: str, value: Any, updates: dict[str, Any]) -> int:
        records = self.read_all(name)
        updated = 0
        for r in records:
            if r.get(key) == value:
                r.update(updates)
                updated += 1
        if updated:
            path = self.data_dir / f"{name}.jsonl"
            with self._lock(name):
                path.write_text(
                    "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
                    encoding="utf-8",
                )
        return updated

    def delete_where(self, name: str, *, key: str, value: Any) -> int:
        records = self.read_all(name)
        kept = [r for r in records if r.get(key) != value]
        deleted = len(records) - len(kept)
        if deleted:
            path = self.data_dir / f"{name}.jsonl"
            with self._lock(name):
                path.write_text(
                    "\n".join(json.dumps(r, ensure_ascii=False) for r in kept) + "\n",
                    encoding="utf-8",
                )
        return deleted

    def health_check(self) -> bool:
        try:
            test_path = self.data_dir / ".health"
            test_path.write_text("ok")
            test_path.unlink()
            return True
        except OSError:
            return False


# Singleton for ClawCode compat patterns.
_db_instance: Database | None = None


def get_database() -> Database:
    """Return the global Database instance (creates one in ~/.kageko if needed)."""
    global _db_instance
    if _db_instance is None:
        from pathlib import Path
        _db_instance = Database(Path.home() / ".kageko" / "data")
    return _db_instance
