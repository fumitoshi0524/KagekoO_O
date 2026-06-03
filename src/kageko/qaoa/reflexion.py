"""Post-session Reflexion analysis.

After each session, analyzes QAOA trajectory for failure→recovery patterns.
Extracts concrete "lessons learned" and stores them as facts in Memory.

Based on: Reflexion: Language Agents with Verbal Reinforcement Learning
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from kageko.types import Message

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB
    from kageko.learning.memory_store import MemoryStore

logger = logging.getLogger("kageko.qaoa.reflexion")


_REFLECTION_PROMPT = """\
Analyze this agent trajectory and extract ONE concrete lesson from any
failure or recovery pattern.  Focus on what the agent learned the hard way.

Rules:
- If the agent hit an error then recovered: extract the workaround as a
  declarative fact the agent can use next time.
  Example: "On Windows, native_shell cd /d works for drive changes but bash cd fails — use native_shell for cross-drive directory operations."
- If the agent got stuck or kept retrying the same failing approach:
  extract what strategy change finally worked.
- If the agent avoided a tool that kept failing, or switched strategies mid-task:
  note the preference.
- If there were NO errors or interesting recoveries, respond: NONE
- Write the lesson in **English**, declarative style, one sentence (≤140 chars).
- Return ONLY the lesson text, or the word NONE.

Trajectory (key turns):
{trajectory_summary}

Lesson (or NONE):"""


class ReflexionAnalyzer:
    """Post-session: analyze failures → extract lessons → store in Memory."""

    def __init__(self, db: KagekoDB, memory_store: MemoryStore | None = None):
        self.db = db
        self.memory = memory_store

    async def analyze_session(self, session_id: str, llm) -> str | None:
        """Analyze one session's trajectory and store a lesson if found.

        Returns the lesson text, or None if nothing worth saving.
        """
        messages = await self.db.get_messages(session_id)
        if not messages:
            return None

        # Build a compact summary: key turns with errors
        summary = self._build_trajectory_summary(messages)
        if not summary:
            return None

        prompt = _REFLECTION_PROMPT.format(trajectory_summary=summary)

        try:
            response = await llm.chat([Message(role="user", content=prompt)])
            lesson = (response.content or "").strip()
        except Exception:
            logger.debug("Reflexion LLM call failed", exc_info=True)
            return None

        if not lesson or lesson.upper() == "NONE":
            return None

        # Store in memory if available
        if self.memory:
            await self.memory.add(lesson, source="reflexion")

        logger.info("Reflexion: extracted lesson — %s", lesson[:80])
        return lesson

    async def analyze_recent(self, llm, days: int = 7) -> list[str]:
        """Analyze all sessions from the past N days. Returns lessons extracted."""
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = await self.db._conn.execute(
            "SELECT id FROM sessions WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,),
        )
        rows = await cursor.fetchall()
        lessons: list[str] = []
        for row in rows:
            lesson = await self.analyze_session(row["id"], llm)
            if lesson:
                lessons.append(lesson)
        return lessons

    # ── Internal ────────────────────────────────────────────────────────

    def _build_trajectory_summary(self, messages) -> str:
        """Extract error turns and recovery patterns from message history."""
        lines: list[str] = []
        in_error = False

        for msg in messages:
            role = getattr(msg, "role", "?")
            content = str(getattr(msg, "content", ""))[:200]

            if role == "tool":
                is_err = "[ERROR]" in content or "[EXIT" in content
                if is_err:
                    lines.append(f"[ERROR] {content}")
                    in_error = True
                elif in_error:
                    # This is the first non-error after an error → possible recovery
                    lines.append(f"[RECOVERY] {content}")
                    in_error = False
                else:
                    lines.append(f"[tool] {content[:100]}")
            elif role == "user":
                lines.append(f"[user] {content[:200]}")
            # skip assistant/system in summary

        return "\n".join(lines[-30:]) if lines else ""  # last 30 relevant lines
