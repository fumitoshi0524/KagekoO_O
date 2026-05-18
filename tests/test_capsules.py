from __future__ import annotations

import tempfile
from pathlib import Path

from qaoa.experience.capsules import ECAPStore, ExperienceCapsule


def test_record_and_retrieve_capsule():
    with tempfile.TemporaryDirectory() as td:
        store = ECAPStore(_store_dir=Path(td))
        cap = store.record(
            skill_name="test-skill", skill_version="v1",
            query="analyze data", tool_trajectory=["file.read", "bash.run"],
            outcome="Analysis complete",
            scores={"toolfit": 8.0, "clarity": 7.5, "naturalness": 9.0},
            lessons="Need better error handling",
        )
        assert cap.skill_name == "test-skill"
        assert cap.skill_version == "v1"

        capsules = store.get_for_skill("test-skill")
        assert len(capsules) == 1
        assert capsules[0].tool_trajectory == ["file.read", "bash.run"]


def test_quality_score():
    cap = ExperienceCapsule(
        capsule_id="test-1", skill_name="s", skill_version="v1",
        query="q", tool_trajectory=["echo"], outcome="ok",
        scores={"toolfit": 8.0, "clarity": 7.0, "naturalness": 9.0},
    )
    assert cap.quality_score() == 8.0


def test_quality_score_empty():
    cap = ExperienceCapsule(
        capsule_id="test-2", skill_name="s", skill_version="v1",
        query="q", tool_trajectory=[], outcome="ok",
    )
    assert cap.quality_score() == 0.0


def test_to_regeneration_context():
    cap = ExperienceCapsule(
        capsule_id="test-3", skill_name="my-skill", skill_version="v2",
        query="do something", tool_trajectory=["file.read", "bash.run"],
        outcome="success", scores={"toolfit": 7.0}, lessons="use better tools",
    )
    ctx = cap.to_regeneration_context()
    assert "my-skill" in ctx
    assert "v2" in ctx
    assert "use better tools" in ctx


def test_get_lessons_aggregate():
    with tempfile.TemporaryDirectory() as td:
        store = ECAPStore(_store_dir=Path(td))
        store.record(skill_name="s", skill_version="v1", query="q1",
                     tool_trajectory=["echo"], outcome="ok",
                     lessons="Lesson A")
        store.record(skill_name="s", skill_version="v1", query="q2",
                     tool_trajectory=["echo"], outcome="ok",
                     lessons="Lesson B")
        lessons = store.get_lessons("s")
        assert "Lesson A" in lessons
        assert "Lesson B" in lessons


def test_summarize_for_regeneration():
    with tempfile.TemporaryDirectory() as td:
        store = ECAPStore(_store_dir=Path(td))
        store.record(skill_name="s", skill_version="v1", query="q",
                     tool_trajectory=["echo"], outcome="ok",
                     scores={"toolfit": 5.0})
        summary = store.summarize_for_regeneration("s")
        assert "Past Experiences" in summary
        assert "s" in summary
