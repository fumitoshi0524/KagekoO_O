"""Skill registry — central store for all skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..types import SkillSpec

if TYPE_CHECKING:
    from ..adapters.tools import ToolRegistry


@dataclass(slots=True, kw_only=True)
class SkillRegistry:
    _skills: dict[str, SkillSpec] = field(default_factory=dict)
    _active_skill: str | None = None
    _tools: ToolRegistry | None = None

    # ── CRUD ─────────────────────────────────────────────────────────

    def register(self, skill: SkillSpec) -> None:
        self._skills[skill.name] = skill

    def unregister(self, name: str) -> None:
        if name in self._skills:
            del self._skills[name]
        if self._active_skill == name:
            self._active_skill = None

    def get(self, name: str) -> SkillSpec | None:
        return self._skills.get(name)

    def list_all(self) -> list[SkillSpec]:
        return sorted(self._skills.values(), key=lambda s: s.name)

    def count(self) -> int:
        return len(self._skills)

    # ── Activation ───────────────────────────────────────────────────

    def activate(self, name: str) -> None:
        if name not in self._skills:
            raise ValueError(f"Skill '{name}' is not registered.")
        self._active_skill = name

    def deactivate(self) -> None:
        self._active_skill = None

    def get_active(self) -> SkillSpec | None:
        if self._active_skill is None:
            return None
        return self._skills.get(self._active_skill)

    # ── Search ───────────────────────────────────────────────────────

    def search(self, query: str) -> list[SkillSpec]:
        q = query.lower()
        results: list[SkillSpec] = []
        for skill in self._skills.values():
            if (
                q in skill.name.lower()
                or q in skill.description.lower()
                or q in skill.instructions.lower()
            ):
                results.append(skill)
        return sorted(results, key=lambda s: s.name)

    def find_matching(self, query: str) -> list[SkillSpec]:
        """Keyword-based matching. Returns best matches first."""
        q = query.lower()
        words = set(q.split())
        scored: list[tuple[int, SkillSpec]] = []
        for skill in self._skills.values():
            score = 0
            name_lower = skill.name.lower().replace("-", " ").replace("_", " ")
            desc_lower = skill.description.lower()
            # Full query match (highest weight)
            if q in name_lower:
                score += 15
            elif any(w in name_lower for w in words if len(w) > 2):
                score += 8
            if q in desc_lower:
                score += 8
            elif any(w in desc_lower for w in words if len(w) > 2):
                score += 4
            # Word overlap in instructions
            if q in skill.instructions.lower():
                score += 2
            elif any(w in skill.instructions.lower() for w in words if len(w) > 2):
                score += 1
            # Tag matching
            for tag in skill.metadata.get("tags", []):
                tag_str = str(tag).lower()
                if q in tag_str:
                    score += 5
                elif any(w in tag_str for w in words if len(w) > 2):
                    score += 2
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [skill for _, skill in scored]

    # ── Tool binding ─────────────────────────────────────────────────

    def bind_tools(self, tools: ToolRegistry) -> None:
        self._tools = tools

    def get_tools_for_active(self) -> dict[str, object] | None:
        if self._tools is None:
            return None
        active = self.get_active()
        if active is None:
            return None
        return {
            name: self._tools.describe(name)
            for name in active.allowed_tools
            if name in self._tools._specs
        }

    def validate_skill_tools(self, skill: SkillSpec) -> list[str]:
        """Return list of tool names in skill.allowed_tools that don't exist."""
        if self._tools is None:
            return []
        missing: list[str] = []
        for name in skill.allowed_tools:
            if name not in self._tools._specs:
                missing.append(name)
        return missing
