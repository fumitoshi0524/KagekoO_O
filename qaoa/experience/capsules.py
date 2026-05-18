"""ECAP (Experience Capsule) — structured records capturing skill execution outcomes.

Each capsule captures: query, skill version, tool trajectory, outcome scores, lessons learned.
Serialized to JSONL for persistence and feeds back into regeneration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True, kw_only=True)
class ExperienceCapsule:
    """A single experience capsule capturing what was learned from a skill execution."""
    capsule_id: str
    skill_name: str
    skill_version: str
    query: str
    tool_trajectory: list[str]  # ordered list of tool names called
    outcome: str               # final answer or error
    scores: dict[str, float] = field(default_factory=dict)  # toolfit, clarity, naturalness
    lessons: str = ""          # what was learned
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def quality_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)

    def to_regeneration_context(self) -> str:
        """Format this capsule as context for the regeneration engine."""
        lines = [
            f"Experience from skill '{self.skill_name}' (v{self.skill_version}):",
            f"Query: {self.query}",
            f"Tool trajectory: {' → '.join(self.tool_trajectory)}",
            f"Outcome: {self.outcome[:200]}",
            f"Quality: {self.quality_score():.1f}/10",
        ]
        if self.lessons:
            lines.append(f"Lesson: {self.lessons}")
        return "\n".join(lines)


@dataclass(slots=True, kw_only=True)
class ECAPStore:
    """Persistent store for experience capsules using JSONL."""

    _store_dir: Path = field(default_factory=lambda: Path.home() / ".kageko" / "ecaps")
    _capsules: dict[str, list[ExperienceCapsule]] = field(default_factory=dict)

    def __post_init__(self):
        self._store_dir.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        skill_name: str,
        skill_version: str,
        query: str,
        tool_trajectory: list[str],
        outcome: str,
        scores: dict[str, float] | None = None,
        lessons: str = "",
    ) -> ExperienceCapsule:
        """Record a new experience capsule."""
        capsule_id = f"{skill_name}-{int(time.time())}"
        capsule = ExperienceCapsule(
            capsule_id=capsule_id,
            skill_name=skill_name,
            skill_version=skill_version,
            query=query,
            tool_trajectory=tool_trajectory,
            outcome=outcome,
            scores=scores or {},
            lessons=lessons,
        )
        self._capsules.setdefault(skill_name, []).append(capsule)
        self._write_capsule(capsule)
        return capsule

    def get_for_skill(self, skill_name: str, limit: int = 10) -> list[ExperienceCapsule]:
        """Get recent capsules for a skill, most recent first."""
        capsules = self._load_capsules(skill_name)
        capsules.sort(key=lambda c: c.timestamp, reverse=True)
        return capsules[:limit]

    def get_lessons(self, skill_name: str) -> str:
        """Aggregate lessons from all capsules for a skill."""
        capsules = self.get_for_skill(skill_name)
        lessons = [c.lessons for c in capsules if c.lessons]
        if not lessons:
            return ""
        return "\n---\n".join(lessons)

    def summarize_for_regeneration(self, skill_name: str) -> str:
        """Create a summary of experiences to feed into regeneration."""
        capsules = self.get_for_skill(skill_name, limit=5)
        if not capsules:
            return ""
        parts = ["# Past Experiences\n"]
        for c in capsules:
            parts.append(c.to_regeneration_context())
        return "\n".join(parts)

    def _capsule_path(self, skill_name: str) -> Path:
        safe = skill_name.replace("/", "_").replace("\\", "_")
        return self._store_dir / f"{safe}_ecaps.jsonl"

    def _write_capsule(self, capsule: ExperienceCapsule) -> None:
        path = self._capsule_path(capsule.skill_name)
        record = {
            "capsule_id": capsule.capsule_id,
            "skill_name": capsule.skill_name,
            "skill_version": capsule.skill_version,
            "query": capsule.query,
            "tool_trajectory": capsule.tool_trajectory,
            "outcome": capsule.outcome,
            "scores": capsule.scores,
            "lessons": capsule.lessons,
            "timestamp": capsule.timestamp,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_capsules(self, skill_name: str) -> list[ExperienceCapsule]:
        path = self._capsule_path(skill_name)
        if not path.exists():
            return []
        capsules: list[ExperienceCapsule] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                capsules.append(ExperienceCapsule(
                    capsule_id=data["capsule_id"],
                    skill_name=data["skill_name"],
                    skill_version=data["skill_version"],
                    query=data["query"],
                    tool_trajectory=data["tool_trajectory"],
                    outcome=data["outcome"],
                    scores=data.get("scores", {}),
                    lessons=data.get("lessons", ""),
                    timestamp=data.get("timestamp", 0),
                ))
            except (KeyError, json.JSONDecodeError):
                continue
        return capsules
