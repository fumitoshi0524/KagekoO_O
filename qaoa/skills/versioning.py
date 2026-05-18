"""Skill versioning — version history, diff, and JSONL persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import time
from typing import Any

from ..types import SkillSpec


@dataclass(slots=True, frozen=True, kw_only=True)
class SkillVersion:
    """A single version of a skill."""
    version_id: str          # e.g. "v1", "v2", or timestamp-based
    skill: SkillSpec
    timestamp: float         # epoch seconds
    eval_score: float | None = None  # aggregated eval score
    changes: str = ""        # human-readable change summary
    parent_version: str | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class SkillDiff:
    """Structural diff between two skill versions."""
    name: str
    old_version: str
    new_version: str
    description_changed: bool = False
    category_changed: bool = False
    domain_changed: bool = False
    tools_added: list[str] = field(default_factory=list)
    tools_removed: list[str] = field(default_factory=list)
    permissions_added: list[str] = field(default_factory=list)
    permissions_removed: list[str] = field(default_factory=list)
    instructions_replaced: bool = False  # True if instructions changed significantly
    score_delta: float | None = None     # eval score change


class SkillHistory:
    """Manages version history for skills with JSONL persistence."""

    def __init__(self, history_dir: Path | None = None) -> None:
        self._history_dir = history_dir or Path.home() / ".kageko" / "skill_history"
        self._history_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, list[SkillVersion]] = {}

    def record_version(
        self,
        skill: SkillSpec,
        *,
        eval_score: float | None = None,
        changes: str = "",
    ) -> SkillVersion:
        """Record a new version of a skill. Auto-increments version counter."""
        existing = self.get_history(skill.name)
        version_num = len(existing) + 1
        parent = existing[-1].version_id if existing else None

        version = SkillVersion(
            version_id=f"v{version_num}",
            skill=skill,
            timestamp=time.time(),
            eval_score=eval_score,
            changes=changes,
            parent_version=parent,
        )
        self._cache.setdefault(skill.name, []).append(version)
        self._append_to_file(skill.name, version)
        return version

    def get_history(self, skill_name: str) -> list[SkillVersion]:
        """Get all versions of a skill, ordered oldest first."""
        if skill_name not in self._cache:
            self._load_history(skill_name)
        return self._cache.get(skill_name, [])

    def get_latest(self, skill_name: str) -> SkillVersion | None:
        history = self.get_history(skill_name)
        return history[-1] if history else None

    def get_by_score(self, skill_name: str) -> SkillVersion | None:
        """Get the highest-scoring version."""
        history = self.get_history(skill_name)
        if not history:
            return None
        return max(
            (v for v in history if v.eval_score is not None),
            key=lambda v: v.eval_score or 0,
            default=history[-1],
        )

    def _history_path(self, skill_name: str) -> Path:
        safe_name = skill_name.replace("/", "_").replace("\\", "_")
        return self._history_dir / f"{safe_name}.jsonl"

    def _load_history(self, skill_name: str) -> None:
        path = self._history_path(skill_name)
        if not path.exists():
            self._cache[skill_name] = []
            return
        versions: list[SkillVersion] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                skill = SkillSpec(
                    name=data["skill"]["name"],
                    description=data["skill"]["description"],
                    instructions=data["skill"]["instructions"],
                    allowed_tools=data["skill"].get("allowed_tools", []),
                    permissions=data["skill"].get("permissions", []),
                    metadata=data["skill"].get("metadata", {}),
                    format=data["skill"].get("format", "qaoa-uni-tool-call"),
                )
                version = SkillVersion(
                    version_id=data["version_id"],
                    skill=skill,
                    timestamp=data["timestamp"],
                    eval_score=data.get("eval_score"),
                    changes=data.get("changes", ""),
                    parent_version=data.get("parent_version"),
                )
                versions.append(version)
            except (KeyError, json.JSONDecodeError):
                continue
        self._cache[skill_name] = versions

    def _append_to_file(self, skill_name: str, version: SkillVersion) -> None:
        path = self._history_path(skill_name)
        record = {
            "version_id": version.version_id,
            "skill": {
                "name": version.skill.name,
                "description": version.skill.description,
                "instructions": version.skill.instructions,
                "allowed_tools": version.skill.allowed_tools,
                "permissions": version.skill.permissions,
                "metadata": version.skill.metadata,
                "format": version.skill.format,
            },
            "timestamp": version.timestamp,
            "eval_score": version.eval_score,
            "changes": version.changes,
            "parent_version": version.parent_version,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def diff_skills(old: SkillSpec, new: SkillSpec) -> SkillDiff:
    """Compute structural diff between two skill specs."""
    old_cat = old.metadata.get("category", "")
    new_cat = new.metadata.get("category", "")
    old_dom = old.metadata.get("domain", "")
    new_dom = new.metadata.get("domain", "")

    old_tools = set(old.allowed_tools)
    new_tools = set(new.allowed_tools)
    old_perms = set(old.permissions)
    new_perms = set(new.permissions)

    return SkillDiff(
        name=old.name,
        old_version="old",
        new_version="new",
        description_changed=old.description != new.description,
        category_changed=old_cat != new_cat,
        domain_changed=old_dom != new_dom,
        tools_added=sorted(new_tools - old_tools),
        tools_removed=sorted(old_tools - new_tools),
        permissions_added=sorted(new_perms - old_perms),
        permissions_removed=sorted(old_perms - new_perms),
        instructions_replaced=old.instructions != new.instructions,
    )
