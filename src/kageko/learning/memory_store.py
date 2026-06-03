"""Pure memory storage with FTS5 search, hard char limits, and frozen snapshots.

Hermes principle: hard character limits force curation. Stale/less-important
facts are naturally displaced by newer ones.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB

logger = logging.getLogger("kageko.learning.store")

# Hermes-style hard limits
MAX_FACTS = 50          # keep at most N facts
SNAPSHOT_CHAR_LIMIT = 3000  # system-prompt block cap


@dataclass
class Fact:
    id: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = "fact"
    created_at: str = ""


class MemoryStore:
    """Cross-session declarative-fact store.

    Facts are short, declarative, and written in English regardless of
    conversation language.  The snapshot is frozen at session start and
    injected into the system prompt exactly once.
    """

    def __init__(self, db: KagekoDB, *, char_limit: int = SNAPSHOT_CHAR_LIMIT):
        self.db = db
        self.char_limit = char_limit
        self._snapshot: str = ""

    # ── Snapshot (session-start freeze) ─────────────────────────────────

    async def load_snapshot(self) -> str:
        """Load recent facts, trim to char_limit, freeze for the session."""
        rows = await self.db.list_memory(limit=100)
        facts = [r.content for r in rows if r.source in ("fact", "conversation")]
        if not facts:
            self._snapshot = ""
            return ""

        parts: list[str] = []
        total = 0
        for fact in facts:  # newest first from DB
            if total + len(fact) + 3 > self.char_limit:
                break
            parts.append(f"- {fact}")
            total += len(fact) + 3

        self._snapshot = "\n".join(parts)
        return self._snapshot

    @property
    def snapshot(self) -> str:
        return self._snapshot

    # ── CRUD ────────────────────────────────────────────────────────────

    async def add(self, fact_text: str, source: str = "fact") -> Fact:
        """Store a single fact. Enforces MAX_FACTS limit by trimming oldest."""
        import hashlib
        now = datetime.now().isoformat()
        fid = f"fact-{now}-{hashlib.md5(fact_text.encode()).hexdigest()[:8]}"

        current = await self.db.get_memory_count()
        if current >= MAX_FACTS:
            await self._trim_oldest(keep=MAX_FACTS - 5)

        await self.db.write_with_retry(
            "INSERT OR REPLACE INTO memory (id, content, tags, source, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (fid, fact_text, "fact", source, ""),
        )
        return Fact(id=fid, content=fact_text, source=source, created_at=now)

    async def add_batch(self, facts: list[str], source: str = "fact") -> int:
        """Store multiple facts. Returns count stored."""
        count = 0
        for f in facts:
            await self.add(f, source=source)
            count += 1
        return count

    async def delete(self, *, fact_id: str = "", substring: str = "") -> int:
        """Delete by ID or content substring. Returns count deleted."""
        if fact_id:
            await self.db._conn.execute("DELETE FROM memory WHERE id = ?", (fact_id,))
            await self.db._conn.commit()
            return 1
        if substring:
            cursor = await self.db._conn.execute(
                "SELECT id FROM memory WHERE content LIKE ?",
                (f"%{substring}%",),
            )
            rows = await cursor.fetchall()
            for r in rows:
                await self.db._conn.execute("DELETE FROM memory WHERE id = ?", (r["id"],))
            await self.db._conn.commit()
            return len(rows)
        return 0

    async def replace(self, old_substring: str, new_text: str) -> int:
        """Find facts containing old_substring, replace with new_text.

        Hermes-style: substring match, exact duplicate detection,
        multi-match error. Returns count of facts replaced.
        """
        cursor = await self.db._conn.execute(
            "SELECT id, content FROM memory WHERE content LIKE ?",
            (f"%{old_substring}%",),
        )
        rows = await cursor.fetchall()
        if not rows:
            return 0

        # Check exact duplicate
        existing_texts = {r["content"] for r in rows}
        if new_text in existing_texts:
            # New text already exists — delete the old one, don't add duplicate
            for r in rows:
                if r["content"] != new_text:
                    await self.db._conn.execute("DELETE FROM memory WHERE id = ?", (r["id"],))
            await self.db._conn.commit()
            return len(rows)

        # Replace first match
        await self.db._conn.execute(
            "UPDATE memory SET content = ? WHERE id = ?",
            (new_text, rows[0]["id"]),
        )
        # Delete any remaining matches (consolidation)
        for r in rows[1:]:
            await self.db._conn.execute("DELETE FROM memory WHERE id = ?", (r["id"],))
        await self.db._conn.commit()
        return len(rows)

    async def usage(self) -> dict:
        """Return {count, char_count, pct, limit} for usage feedback."""
        facts = await self.list(limit=100)
        total_chars = sum(len(f.content) for f in facts)
        pct = min(100, int((total_chars / self.char_limit) * 100)) if self.char_limit > 0 else 0
        return {
            "count": len(facts),
            "char_count": total_chars,
            "pct": pct,
            "limit": self.char_limit,
        }

    async def list(self, limit: int = 20) -> list[Fact]:
        """List recent facts."""
        rows = await self.db.list_memory(limit=limit)
        return [
            Fact(id=r.id, content=r.content, tags=r.tags.split(",") if r.tags else [],
                 source=r.source, created_at=r.created_at)
            for r in rows
        ]

    async def search(self, query: str, limit: int = 5) -> list[Fact]:
        """FTS5 search over memories."""
        rows = await self.db.search_memory(query, limit=limit)
        return [
            Fact(id=r["id"], content=r["content"],
                 tags=r["tags"].split(",") if r["tags"] else [],
                 source=r["source"], created_at=r["created_at"])
            for r in rows
        ]

    async def count(self) -> int:
        return await self.db.get_memory_count()

    async def clear(self) -> None:
        """Delete ALL memories. For testing only."""
        await self.db._conn.execute("DELETE FROM memory")
        await self.db._conn.commit()

    # ── Internal ────────────────────────────────────────────────────────

    async def _trim_oldest(self, keep: int = 40) -> None:
        cursor = await self.db._conn.execute(
            "SELECT id FROM memory WHERE source = 'fact' ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        if len(rows) <= keep:
            return
        for r in rows[: len(rows) - keep]:
            await self.db._conn.execute("DELETE FROM memory WHERE id = ?", (r["id"],))
        await self.db._conn.commit()
