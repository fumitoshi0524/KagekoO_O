"""Hermes-style skill store — progressive loading, self-patch, pin/unpin.

Design:
  - Skill INDEX (name + one-line description) lives in the system prompt.
  - Full skill content loaded on demand via skill_view (auto-touches last_used).
  - Self-patch: surgical find-and-replace, not full rewrite.
  - Pin = protected from curator archival.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB

logger = logging.getLogger("kageko.learning.skills")


@dataclass
class SkillRecord:
    name: str
    version: str
    description: str
    trigger: str
    steps: list[str] = field(default_factory=list)
    content: str = ""
    tags: list[str] = field(default_factory=list)
    state: str = "active"
    pinned: bool = False


class SkillStore:
    """CRUD + lifecycle management for reusable skills.

    The agent's system prompt includes a compact index (name + description).
    When the agent needs a skill, it calls skill_view to load the full content.
    """

    def __init__(self, db: KagekoDB, llm=None):
        self.db = db
        self.llm = llm  # for create_from_conversation
        self._on_created: Any = None  # callback(skill_name, description)

    def set_on_created(self, callback):
        """Register a callback invoked after every skill creation."""
        self._on_created = callback

    # ── Index (compact, for system prompt) ──────────────────────────────

    async def index_text(self) -> str:
        """Return a one-line-per-skill index for the system prompt."""
        skills = await self.db.get_skills_all()
        active = [s for s in skills if getattr(s, "state", "active") == "active"]
        if not active:
            return ""
        lines = ["[Available skills — use skill_view to load full instructions]"]
        for s in active:
            pinned = "📌" if getattr(s, "pinned", 0) else " "
            desc = (getattr(s, "description", "") or "")[:80]
            lines.append(f" {pinned} {s.name}: {desc}")
        return "\n".join(lines)

    # ── View (full content, touch last_used) ────────────────────────────

    async def view(self, name: str) -> SkillRecord | None:
        """Load full skill content. Auto-touches last_used."""
        skills = await self.db.get_skills_all()
        for s in skills:
            if s.name == name:
                await self.db.skill_touch(name)
                return SkillRecord(
                    name=s.name,
                    version=s.version,
                    description=getattr(s, "description", ""),
                    trigger=getattr(s, "trigger", ""),
                    steps=[],
                    content=getattr(s, "content", ""),
                    tags=getattr(s, "tags", []),
                    state=getattr(s, "state", "active"),
                    pinned=bool(getattr(s, "pinned", 0)),
                )
        return None

    # ── CRUD ────────────────────────────────────────────────────────────

    async def save(self, record: SkillRecord) -> None:
        """Persist a skill to DB."""
        await self.db.save_skill(
            name=record.name,
            version=record.version,
            trigger=record.trigger,
            description=record.description,
            content=record.content or "\n".join(record.steps),
            tags=record.tags,
        )

    async def delete(self, name: str) -> bool:
        """Hard-delete a skill."""
        await self.db._conn.execute("DELETE FROM skills WHERE name = ?", (name,))
        await self.db._conn.commit()
        return True

    async def archive(self, name: str) -> bool:
        """Archive a skill (soft-delete, restorable)."""
        return await self.db.skill_set_state(name, "archived")

    async def list_all(self) -> list[SkillRecord]:
        """List all skills regardless of state."""
        skills = await self.db.get_skills_all()
        return [
            SkillRecord(
                name=s.name, version=s.version,
                description=getattr(s, "description", ""),
                trigger=getattr(s, "trigger", ""),
                tags=getattr(s, "tags", []),
                state=getattr(s, "state", "active"),
                pinned=bool(getattr(s, "pinned", 0)),
            )
            for s in skills
        ]

    # ── Pin / Unpin ─────────────────────────────────────────────────────

    async def pin(self, name: str) -> bool:
        return await self.db.skill_pin(name)

    async def unpin(self, name: str) -> bool:
        return await self.db.skill_unpin(name)

    # ── Self-patch (surgical find-and-replace) ──────────────────────────

    async def patch(self, name: str, find: str, replace: str) -> bool:
        """Fuzzy find-and-replace inside a skill's content.

        Hermes principle: when the agent discovers a missing step or outdated
        instruction, it patches only the broken part, not the whole skill.
        """
        return await self.db.skill_patch(name, find, replace)

    # ── Extract from conversation ───────────────────────────────────────

    async def extract_from_conversation(self, history: str) -> SkillRecord | None:
        """LLM-driven skill extraction from conversation text.

        Call this after complex tasks (5+ tool calls), error recovery, or
        user corrections — Hermes' three creation triggers.
        """
        if not self.llm:
            logger.warning("Skill extraction skipped: no LLM wired")
            return None

        from kageko.types import Message

        prompt = (
            "Extract a reusable skill from this conversation. "
            "Write ALL fields (name, description, trigger, steps) in **English**, "
            "regardless of the conversation language.\n"
            "Return JSON: {name, version, description, trigger, tags, steps}.\n\n"
            + history[:3000]
        )

        import json as _json
        try:
            response = await self.llm.chat([Message(role="user", content=prompt)])
            data = _json.loads(response.content)
        except Exception:
            logger.debug("Skill extraction failed", exc_info=True)
            return None

        name = data.get("name", "").strip()
        if not name:
            return None

        record = SkillRecord(
            name=name,
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            trigger=data.get("trigger", ""),
            steps=data.get("steps", []),
            tags=data.get("tags", []),
        )
        await self.save(record)
        if self._on_created:
            try:
                await self._on_created(record.name, record.description)
            except Exception:
                pass  # memory cleanup is best-effort
        logger.info("Extracted skill: %s", name)
        return record
