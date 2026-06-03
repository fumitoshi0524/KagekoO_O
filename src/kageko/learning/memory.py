"""Memory system facade — thin wrapper around MemoryStore + NudgeEngine.

Kept for backward compatibility. New code should import directly from
``kageko.learning.memory_store`` and ``kageko.learning.nudge_engine``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from kageko.learning.memory_store import MemoryStore, Fact
from kageko.learning.nudge_engine import NudgeEngine

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB

logger = logging.getLogger("kageko.learning.memory")

# Re-export
SNAPSHOT_CHAR_LIMIT = 3000


@dataclass
class MemoryEntry:
    """Backward-compat entry type."""
    id: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = "conversation"
    session_id: str = ""
    created_at: datetime | None = None
    relevance_score: float = 0.0


class MemoryManager:
    """Thin facade over MemoryStore + NudgeEngine + SkillStore + Curator.

    All real logic lives in the sub-modules.  This class exists so
    existing wiring (AgentEngine, cli.py, cli_commands.py) doesn't break.
    """

    def __init__(self, db: KagekoDB, *, llm=None, nudge_threshold: int = 10, char_limit: int = SNAPSHOT_CHAR_LIMIT):
        from kageko.learning.skill_store import SkillStore
        from kageko.learning.curator import Curator, CuratorConfig

        self.store = MemoryStore(db, char_limit=char_limit)
        self.nudge_engine = NudgeEngine(self.store, threshold=nudge_threshold)
        self.skill_store = SkillStore(db, llm=llm)
        self.skill_store.set_on_created(self.on_skill_created)
        self.curator = Curator(db, CuratorConfig(interval_hours=168))

    # ── Snapshot (frozen at session start) ──────────────────────────────

    async def load_snapshot(self) -> str:
        return await self.store.load_snapshot()

    @property
    def snapshot(self) -> str:
        return self.store.snapshot

    # ── Nudge Engine (tick + background review) ─────────────────────────

    def nudge_tick(self) -> bool:
        """Tick the nudge counter. Returns True when it's time for a review."""
        return self.nudge_engine.tick()

    async def run_review(self, recent_messages: list, llm) -> list[str]:
        """Run a background fact-extraction review."""
        return await self.nudge_engine.run_review(recent_messages, llm)

    # ── Search (used by AgentEngine for prefetch) ───────────────────────

    async def prefetch(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        rows = await self.store.db.search_memory(query, limit=limit)
        return [
            MemoryEntry(
                id=r["id"], content=r["content"],
                tags=r["tags"].split(",") if r["tags"] else [],
                source=r["source"], session_id=r["session_id"],
            )
            for r in rows
        ]

    # ── Manual store ────────────────────────────────────────────────────

    async def store(self, entry: MemoryEntry) -> None:
        tags_str = ",".join(entry.tags) if entry.tags else ""
        await self.store.db.write_with_retry(
            "INSERT OR REPLACE INTO memory (id, content, tags, source, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (entry.id, entry.content, tags_str, entry.source, entry.session_id),
        )

    # ── Deprecated / no-ops ─────────────────────────────────────────────

    async def on_skill_created(self, skill_name: str, description: str) -> int:
        """Called after a skill is extracted. Upgrades related raw-library
        memories to reference the skill by name."""
        words = set(w.lower() for w in description.split() if len(w) > 4)
        replaced = 0
        for keyword in words:
            count = await self.store.replace(
                keyword, f"Use {skill_name} skill for {description[:80]}"
            )
            replaced += count
        return replaced

    async def sync_turn(self, turn) -> None:
        """No-op kept for backward compat. Use NudgeEngine instead."""

    async def on_pre_compress(self, messages: list) -> list[MemoryEntry]:
        """Extract key info before context compression."""
        entries = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    entries.append(MemoryEntry(
                        id=f"compress-{tc.name}-{datetime.now().isoformat()}",
                        content=self.summarize_tool_result(tc.name, str(getattr(tc, "result", ""))),
                        tags=["compressed"], source="tool_result",
                    ))
        return entries

    def summarize_tool_result(self, tool_name: str, result: str) -> str:
        """Generate a one-line tool result summary."""
        lines = result.strip().split("\n")
        lc = len(lines)
        if tool_name == "run_bash":
            m = re.search(r"(\d+)\s+failed[,\s]+(\d+)\s+passed", result, re.IGNORECASE)
            if m:
                return f"[run_bash] -> {m.group(1)} failed, {m.group(2)} passed"
            if re.search(r"FAILED|failed|ERROR", result):
                return f"[run_bash] -> errors, {lc} lines"
            return f"[run_bash] -> exit 0, {lc} lines"
        elif tool_name in ("read_file", "file_read"):
            return f"[{tool_name}] -> {lc} lines"
        elif tool_name in ("write_file", "file_write"):
            return f"[{tool_name}] -> wrote {lc} lines"
        elif tool_name in ("grep", "ast_grep"):
            return f"[{tool_name}] -> {sum(1 for l in lines if l.strip())} matches"
        elif tool_name == "web_search":
            return f"[web_search] -> {lc} lines"
        else:
            preview = result[:80].replace("\n", " ")
            if len(result) > 80:
                preview += "..."
            return f"[{tool_name}] -> {preview}"
