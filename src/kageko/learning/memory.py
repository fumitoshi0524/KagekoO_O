from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB


@dataclass
class MemoryEntry:
    id: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = "conversation"  # 'conversation', 'tool_result', 'skill'
    session_id: str = ""
    created_at: datetime | None = None
    relevance_score: float = 0.0


class MemoryManager:
    """Cross-session memory with FTS5 recall and tool result summarization."""

    def __init__(self, db: KagekoDB):
        self.db = db

    async def prefetch(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Recall relevant memories via FTS5 search."""
        rows = await self.db.search_memory(query, limit=limit)
        return [
            MemoryEntry(
                id=r["id"],
                content=r["content"],
                tags=r["tags"].split(",") if r["tags"] else [],
                source=r["source"],
                session_id=r["session_id"],
            )
            for r in rows
        ]

    async def sync_turn(self, turn) -> None:
        """Persist key information from a conversation turn."""
        if turn and hasattr(turn, "user") and turn.user:
            await self.store(MemoryEntry(
                id=f"turn-{datetime.now().isoformat()}",
                content=turn.user[:500] if isinstance(turn.user, str) else str(turn.user)[:500],
                source="conversation",
                session_id=getattr(turn, "session_id", ""),
            ))

    async def on_pre_compress(self, messages: list) -> list[MemoryEntry]:
        """Extract key information before context compression discards messages."""
        entries = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    entries.append(MemoryEntry(
                        id=f"compress-{tc.name}-{datetime.now().isoformat()}",
                        content=self.summarize_tool_result(tc.name, str(getattr(tc, "result", ""))),
                        tags=["compressed"],
                        source="tool_result",
                    ))
        return entries

    async def store(self, entry: MemoryEntry) -> None:
        """Write a memory entry to the database."""
        tags_str = ",".join(entry.tags) if entry.tags else ""
        await self.db.write_with_retry(
            "INSERT OR REPLACE INTO memory (id, content, tags, source, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (entry.id, entry.content, tags_str, entry.source, entry.session_id),
        )

    def summarize_tool_result(self, tool_name: str, result: str) -> str:
        """Generate a meaningful one-line summary of a tool result.

        Examples:
            [run_bash] ran pytest -> 47 failed, 2 passed
            [read_file] read src/auth.py -> 142 lines
        """
        lines = result.strip().split("\n")
        line_count = len(lines)

        if tool_name == "run_bash":
            # Try to extract pytest-style summary: "N failed, M passed"
            summary_match = re.search(
                r"(\d+)\s+failed[,\s]+(\d+)\s+passed", result, re.IGNORECASE
            )
            if summary_match:
                return f"[run_bash] -> {summary_match.group(1)} failed, {summary_match.group(2)} passed"
            if "FAILED" in result or "failed" in result.lower():
                fail_count = sum(
                    1 for l in lines
                    if "FAILED" in l or "failed" in l.lower() or "ERROR" in l
                )
                return f"[run_bash] -> {fail_count} failures, {line_count} lines output"
            elif "error" in result.lower() or "Error" in result:
                return f"[run_bash] -> error, {line_count} lines output"
            else:
                return f"[run_bash] -> exit 0, {line_count} lines output"

        elif tool_name in ("read_file", "file_read"):
            return f"[{tool_name}] -> {line_count} lines"

        elif tool_name in ("write_file", "file_write"):
            return f"[{tool_name}] -> wrote {line_count} lines"

        elif tool_name in ("grep", "ast_grep"):
            match_count = sum(1 for l in lines if l.strip())
            return f"[{tool_name}] -> {match_count} matches"

        elif tool_name == "web_search":
            return f"[web_search] -> {line_count} lines result"

        else:
            preview = result[:80].replace("\n", " ")
            if len(result) > 80:
                preview += "..."
            return f"[{tool_name}] -> {preview}"
