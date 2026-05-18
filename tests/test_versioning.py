from __future__ import annotations

import tempfile
from pathlib import Path

from qaoa.skills.versioning import SkillHistory, diff_skills
from qaoa.types import SkillSpec


def make_skill(name="test", **kwargs):
    defaults = {
        "name": name, "description": "test skill", "instructions": "Step 1\nStep 2",
        "allowed_tools": ["file.read"], "permissions": ["read"],
        "metadata": {"category": "analysis", "domain": "science"}, "format": "qaoa-uni-tool-call",
    }
    defaults.update(kwargs)
    return SkillSpec(**defaults)


def test_record_and_retrieve_version():
    with tempfile.TemporaryDirectory() as td:
        hist = SkillHistory(Path(td))
        v1 = hist.record_version(make_skill("test-skill"), eval_score=7.5, changes="initial")
        assert v1.version_id == "v1"
        assert v1.eval_score == 7.5
        history = hist.get_history("test-skill")
        assert len(history) == 1
        assert history[0].skill.name == "test-skill"


def test_multiple_versions():
    with tempfile.TemporaryDirectory() as td:
        hist = SkillHistory(Path(td))
        hist.record_version(make_skill("s"), eval_score=6.0)
        hist.record_version(make_skill("s"), eval_score=8.0)
        assert len(hist.get_history("s")) == 2
        latest = hist.get_latest("s")
        assert latest.version_id == "v2"


def test_get_by_score():
    with tempfile.TemporaryDirectory() as td:
        hist = SkillHistory(Path(td))
        hist.record_version(make_skill("s"), eval_score=3.0)
        hist.record_version(make_skill("s"), eval_score=9.0)
        hist.record_version(make_skill("s"), eval_score=6.0)
        best = hist.get_by_score("s")
        assert best.eval_score == 9.0


def test_get_history_empty():
    with tempfile.TemporaryDirectory() as td:
        hist = SkillHistory(Path(td))
        assert hist.get_history("nonexistent") == []
        assert hist.get_latest("nonexistent") is None


def test_diff_skills_detects_changes():
    old = make_skill("s", description="v1", allowed_tools=["file.read"], permissions=["read"])
    new = make_skill("s", description="v2", allowed_tools=["file.read", "file.write"], permissions=["read", "write"])
    d = diff_skills(old, new)
    assert d.description_changed
    assert d.tools_added == ["file.write"]
    assert d.permissions_added == ["write"]
    assert d.tools_removed == []
    assert d.permissions_removed == []


def test_diff_skills_detects_category_change():
    old = make_skill("s", metadata={"category": "analysis", "domain": "science"})
    new = make_skill("s", metadata={"category": "operations", "domain": "science"})
    d = diff_skills(old, new)
    assert d.category_changed
    assert not d.domain_changed
