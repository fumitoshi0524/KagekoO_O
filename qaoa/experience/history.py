"""Performance history — per-skill tracking of eval scores, usage, and regen history.

Surfaces skills that have degraded and need regeneration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from pathlib import Path
from typing import Any


@dataclass(slots=True, kw_only=True)
class SkillPerformanceRecord:
    """A single performance data point for a skill."""
    skill_name: str
    timestamp: float
    eval_score: float | None = None
    usage_count: int = 0
    failure_count: int = 0
    regeneration_count: int = 0
    last_regenerated: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def failure_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.failure_count / self.usage_count

    def is_degraded(self, quality_threshold: float = 6.0) -> bool:
        """A skill is degraded if its score is below threshold or failure rate is high."""
        if self.eval_score is not None and self.eval_score < quality_threshold:
            return True
        if self.failure_rate > 0.3:  # >30% failure rate
            return True
        return False


@dataclass(slots=True, kw_only=True)
class PerformanceHistory:
    """Tracks and persists performance history for all skills."""

    _store_dir: Path = field(default_factory=lambda: Path.home() / ".kageko" / "perf_history")
    _records: dict[str, list[SkillPerformanceRecord]] = field(default_factory=dict)

    def __post_init__(self):
        self._store_dir.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        skill_name: str,
        eval_score: float | None = None,
        usage_delta: int = 0,
        failure: bool = False,
        regenerated: bool = False,
    ) -> SkillPerformanceRecord:
        """Record a performance data point for a skill."""
        now = time.time()
        existing = self._records.setdefault(skill_name, [])
        prev = existing[-1] if existing else None

        record = SkillPerformanceRecord(
            skill_name=skill_name,
            timestamp=now,
            eval_score=eval_score,
            usage_count=(prev.usage_count if prev else 0) + usage_delta,
            failure_count=(prev.failure_count if prev else 0) + (1 if failure else 0),
            regeneration_count=(prev.regeneration_count if prev else 0) + (1 if regenerated else 0),
            last_regenerated=now if regenerated else (prev.last_regenerated if prev else None),
        )
        existing.append(record)
        self._write_record(record)
        return record

    def get_latest(self, skill_name: str) -> SkillPerformanceRecord | None:
        records = self._records.get(skill_name) or self._load_records(skill_name)
        return records[-1] if records else None

    def get_degraded_skills(self, quality_threshold: float = 6.0) -> list[str]:
        """Return names of skills that have degraded and need regeneration."""
        degraded: list[str] = []
        for name in set(self._records) | self._list_tracked_skills():
            latest = self.get_latest(name)
            if latest and latest.is_degraded(quality_threshold):
                degraded.append(name)
        return degraded

    def _history_path(self, skill_name: str) -> Path:
        safe = skill_name.replace("/", "_").replace("\\", "_")
        return self._store_dir / f"{safe}_perf.jsonl"

    def _write_record(self, record: SkillPerformanceRecord) -> None:
        path = self._history_path(record.skill_name)
        entry = {
            "skill_name": record.skill_name,
            "timestamp": record.timestamp,
            "eval_score": record.eval_score,
            "usage_count": record.usage_count,
            "failure_count": record.failure_count,
            "regeneration_count": record.regeneration_count,
            "last_regenerated": record.last_regenerated,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_records(self, skill_name: str) -> list[SkillPerformanceRecord]:
        path = self._history_path(skill_name)
        if not path.exists():
            return []
        records: list[SkillPerformanceRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                records.append(SkillPerformanceRecord(
                    skill_name=data["skill_name"],
                    timestamp=data["timestamp"],
                    eval_score=data.get("eval_score"),
                    usage_count=data.get("usage_count", 0),
                    failure_count=data.get("failure_count", 0),
                    regeneration_count=data.get("regeneration_count", 0),
                    last_regenerated=data.get("last_regenerated"),
                ))
            except (KeyError, json.JSONDecodeError):
                continue
        self._records[skill_name] = records
        return records

    def _list_tracked_skills(self) -> set[str]:
        names: set[str] = set()
        for path in self._store_dir.glob("*_perf.jsonl"):
            stem = path.stem.replace("_perf", "")
            names.add(stem.replace("_", "/"))
        return names
