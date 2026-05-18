from __future__ import annotations

import tempfile
from pathlib import Path

from qaoa.experience.history import PerformanceHistory, SkillPerformanceRecord


def test_record_usage():
    with tempfile.TemporaryDirectory() as td:
        perf = PerformanceHistory(_store_dir=Path(td))
        record = perf.record(skill_name="s", usage_delta=5, failure=False)
        assert record.usage_count == 5
        assert record.failure_count == 0
        assert record.failure_rate == 0.0


def test_record_failure():
    with tempfile.TemporaryDirectory() as td:
        perf = PerformanceHistory(_store_dir=Path(td))
        perf.record(skill_name="s", usage_delta=3, failure=False)
        perf.record(skill_name="s", usage_delta=2, failure=True)
        latest = perf.get_latest("s")
        assert latest.usage_count == 5
        assert latest.failure_count == 1
        assert latest.failure_rate == 0.2


def test_is_degraded_low_score():
    record = SkillPerformanceRecord(
        skill_name="s", timestamp=0, eval_score=4.0, usage_count=10, failure_count=0,
    )
    assert record.is_degraded(quality_threshold=6.0)


def test_is_degraded_high_failure():
    record = SkillPerformanceRecord(
        skill_name="s", timestamp=0, eval_score=9.0, usage_count=10, failure_count=8,
    )
    assert record.is_degraded(quality_threshold=6.0)


def test_is_not_degraded():
    record = SkillPerformanceRecord(
        skill_name="s", timestamp=0, eval_score=9.0, usage_count=10, failure_count=0,
    )
    assert not record.is_degraded(quality_threshold=6.0)


def test_get_degraded_skills():
    with tempfile.TemporaryDirectory() as td:
        perf = PerformanceHistory(_store_dir=Path(td))
        perf.record(skill_name="good", eval_score=9.0, usage_delta=5, failure=False)
        perf.record(skill_name="bad", eval_score=3.0, usage_delta=5, failure=False)
        degraded = perf.get_degraded_skills(quality_threshold=6.0)
        assert "bad" in degraded
        assert "good" not in degraded


def test_get_latest_unknown():
    with tempfile.TemporaryDirectory() as td:
        perf = PerformanceHistory(_store_dir=Path(td))
        assert perf.get_latest("nonexistent") is None


def test_regeneration_tracking():
    with tempfile.TemporaryDirectory() as td:
        perf = PerformanceHistory(_store_dir=Path(td))
        perf.record(skill_name="s", usage_delta=1, failure=False)
        perf.record(skill_name="s", regenerated=True)
        latest = perf.get_latest("s")
        assert latest.regeneration_count == 1
        assert latest.last_regenerated is not None
