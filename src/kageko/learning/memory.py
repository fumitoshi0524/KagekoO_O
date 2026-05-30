from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB

from kageko.types import Message

logger = logging.getLogger("kageko.learning.memory")

# Hard character limit for the frozen system-prompt snapshot (Hermes-style).
# Forces curation: stale/less-important facts are displaced by newer ones.
SNAPSHOT_CHAR_LIMIT = 3000


@dataclass
class MemoryEntry:
    id: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = "conversation"  # 'conversation', 'tool_result', 'skill', 'fact'
    session_id: str = ""
    created_at: datetime | None = None
    relevance_score: float = 0.0


class MemoryManager:
    """Cross-session memory with Hermes-style Nudge Engine.

    Instead of dumping every Q&A turn, the Nudge Engine waits until a
    configurable number of turns have passed, then asks the LLM to extract
    *declarative facts* worth persisting.  "If nothing is worth saving,
    say so" — the agent is explicitly allowed to skip noisy turns.

    At session start a frozen snapshot is loaded and injected into the
    system prompt exactly once (preserving prefix-cache behaviour).
    """

    # ---- public API --------------------------------------------------------

    def __init__(self, db: KagekoDB, *, nudge_threshold: int = 10, char_limit: int = SNAPSHOT_CHAR_LIMIT):
        self.db = db
        self.nudge_threshold = nudge_threshold
        self.char_limit = char_limit
        self._turns_since_review = 0

        # Snapshot frozen at session start (injected into system prompt once).
        self._snapshot: str = ""

    # ------------------------------------------------------------------
    # Snapshot (session-start frozen context)
    # ------------------------------------------------------------------

    async def load_snapshot(self) -> str:
        """Load all facts from DB, trim to char_limit, freeze for the session."""
        rows = await self.db.list_memory(limit=100)
        facts = [r.content for r in rows if r.source in ("fact", "conversation")]
        if not facts:
            self._snapshot = ""
            return ""

        # Build snapshot, newest first, respecting char limit
        parts: list[str] = []
        total = 0
        for fact in facts:
            if total + len(fact) > self.char_limit:
                break
            parts.append(f"- {fact}")
            total += len(fact) + 3  # "- " + "\n"

        self._snapshot = "\n".join(parts)
        return self._snapshot

    @property
    def snapshot(self) -> str:
        """Return the frozen snapshot (call load_snapshot() first)."""
        return self._snapshot

    # ------------------------------------------------------------------
    # Nudge Engine (Hermes-style periodic review)
    # ------------------------------------------------------------------

    def nudge(self) -> bool:
        """Increment the turn counter. Return True when it's time for a review.

        The caller should then invoke :meth:`run_review` (ideally as a
        background task so the user is never blocked).
        """
        self._turns_since_review += 1
        if self._turns_since_review >= self.nudge_threshold:
            self._turns_since_review = 0
            return True
        return False

    async def run_review(self, recent_messages: list, llm) -> list[MemoryEntry]:
        """Ask the LLM to extract declarative facts from recent conversation.

        Returns the newly-stored entries (empty list if nothing was worth saving).
        """
        # Build a compact transcript of recent turns
        transcript = self._build_transcript(recent_messages)
        if not transcript.strip():
            return []

        prompt = _EXTRACTION_PROMPT.format(transcript=transcript)

        try:
            response = await llm.chat([Message(role="user", content=prompt)])
            raw = response.content or ""
            logger.info("Nudge review raw response (first 200 chars): %s", raw[:200])
            facts = self._parse_facts(raw)
        except Exception:
            logger.warning("Fact extraction LLM call failed", exc_info=True)
            return []

        if not facts:
            return []

        # Enforce hard limit: remove oldest facts if we'd overflow
        current_count = await self.db.get_memory_count()
        if current_count + len(facts) > 50:  # keep at most 50 facts total
            await self._trim_oldest(keep=40)

        entries: list[MemoryEntry] = []
        for fact_text in facts:
            entry = MemoryEntry(
                id=f"fact-{datetime.now().isoformat()}-{_short_hash(fact_text)}",
                content=fact_text,
                source="fact",
                tags=["fact"],
            )
            await self.store(entry)
            entries.append(entry)

        logger.info("Nudge: stored %d facts", len(entries))
        return entries

    # ------------------------------------------------------------------
    # Search (used by agent loop for prefetch)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Manual store (for tool results, explicit /remember, etc.)
    # ------------------------------------------------------------------

    async def store(self, entry: MemoryEntry) -> None:
        """Write a memory entry to the database."""
        tags_str = ",".join(entry.tags) if entry.tags else ""
        await self.db.write_with_retry(
            "INSERT OR REPLACE INTO memory (id, content, tags, source, session_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (entry.id, entry.content, tags_str, entry.source, entry.session_id),
        )

    # ------------------------------------------------------------------
    # Legacy helpers (kept for context compressor)
    # ------------------------------------------------------------------

    async def sync_turn(self, turn) -> None:
        """DEPRECATED — use Nudge Engine instead.

        Kept as a no-op for backward compatibility; the per-turn dump
        has been replaced by periodic fact extraction.
        """

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

    def summarize_tool_result(self, tool_name: str, result: str) -> str:
        """Generate a meaningful one-line summary of a tool result."""
        lines = result.strip().split("\n")
        line_count = len(lines)

        if tool_name == "run_bash":
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_transcript(self, messages: list) -> str:
        """Build a compact transcript from the last N messages."""
        lines = []
        for m in messages[-20:]:  # last 20 messages (~10 exchanges)
            role = getattr(m, "role", "?")
            content = getattr(m, "content", "")
            if not content:
                continue
            # Truncate long messages
            content = str(content)[:300]
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)

    def _parse_facts(self, llm_response: str) -> list[str]:
        """Parse the LLM's fact-extraction response.

        Expected format: a JSON array of strings, or the literal word "NONE".
        Handles markdown-fenced JSON (common with DeepSeek).
        """
        text = llm_response.strip()
        if text.upper() == "NONE" or text == "":
            return []

        # Strip markdown code fences: ```json ... ``` or ``` ... ```
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        # Try JSON array first
        try:
            facts = json.loads(text)
            if isinstance(facts, list):
                return [str(f).strip() for f in facts if str(f).strip()]
        except json.JSONDecodeError:
            pass

        # Fallback: try to find a JSON array embedded in the response
        try:
            match = re.search(r'\[.*?\]', text, re.DOTALL)
            if match:
                facts = json.loads(match.group())
                if isinstance(facts, list):
                    return [str(f).strip() for f in facts if str(f).strip()]
        except (json.JSONDecodeError, AttributeError):
            pass

        # Last resort: treat each non-empty line as a fact
        lines = [re.sub(r'^[\d]+\.\s*', '', l.strip().lstrip("- ").strip()) for l in text.split("\n")]
        return [l for l in lines if l and len(l) > 6]

    async def _trim_oldest(self, keep: int = 40) -> None:
        """Delete oldest fact entries, keeping at most `keep`."""
        cursor = await self.db._conn.execute(
            "SELECT id FROM memory WHERE source = 'fact' ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        if len(rows) <= keep:
            return
        to_delete = [r["id"] for r in rows[: len(rows) - keep]]
        for mid in to_delete:
            await self.db._conn.execute("DELETE FROM memory WHERE id = ?", (mid,))
        await self.db._conn.commit()


def _short_hash(s: str) -> str:
    """Tiny hash for dedup-friendly IDs."""
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# LLM prompt for fact extraction (Hermes-style: "declarative facts only")
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are a memory curator. Review the following recent conversation transcript
and extract **declarative facts** that are worth remembering across sessions.

Rules:
- Only extract facts that would be useful in future conversations.
  Examples: user preferences ("uses uv, not pip"), project conventions
  ("tests live in tests/"), environment details ("Python 3.13 on Windows"),
  recurring patterns ("always wants concise answers").
- Do NOT extract:
  - Current working directory or absolute file paths (they change)
  - Session IDs, timestamps, or transient identifiers
  - One-off task results ("created file X", "ran command Y")
  - Trivial chit-chat or greetings
  - Anything that won't outlive the current session
- Limit each fact to ONE sentence (max 120 characters).
- If nothing is worth saving, respond with the single word: NONE
- Return ONLY a JSON array of strings. Example: ["User prefers uv over pip"]

Transcript:
{transcript}

Facts (JSON array or NONE):"""
