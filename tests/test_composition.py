from __future__ import annotations

from qaoa.skills.composition import merge_skills, compose_pipeline, find_overlapping
from qaoa.types import SkillSpec


def make_skill(name, domain="technology", tools=None, perms=None):
    return SkillSpec(
        name=name, description=name, instructions=f"{name} instructions",
        allowed_tools=tools or ["file.read"], permissions=perms or ["read"],
        metadata={"domain": domain}, format="qaoa-uni-tool-call",
    )


def test_merge_skills_combines_tools():
    a = make_skill("reader", tools=["file.read"])
    b = make_skill("writer", tools=["file.write"], perms=["write"])
    merged = merge_skills([a, b])
    assert merged is not None
    assert "file.read" in merged.allowed_tools
    assert "file.write" in merged.allowed_tools
    assert "read" in merged.permissions
    assert "write" in merged.permissions
    assert merged.metadata["composition_type"] == "merge"


def test_merge_rejects_different_domains():
    a = make_skill("a", domain="technology")
    b = make_skill("b", domain="science")
    assert merge_skills([a, b]) is None


def test_merge_single_skill_returns_same():
    a = make_skill("only")
    result = merge_skills([a])
    assert result.name == "only"


def test_merge_empty_list():
    assert merge_skills([]) is None


def test_compose_pipeline_sequential():
    a = make_skill("step1", tools=["file.read"])
    b = make_skill("step2", tools=["file.write"], perms=["write"])
    pipeline = compose_pipeline([a, b])
    assert pipeline is not None
    assert "file.read" in pipeline.allowed_tools
    assert "file.write" in pipeline.allowed_tools
    assert pipeline.metadata["composition_type"] == "pipeline"
    assert "step1" in pipeline.instructions
    assert "step2" in pipeline.instructions


def test_find_overlapping_detects_overlap():
    a = make_skill("a", tools=["file.read", "bash.run"])
    b = make_skill("b", tools=["file.read", "file.write"])
    pairs = find_overlapping([a, b])
    assert len(pairs) == 1
    assert pairs[0][0].name in ("a", "b")
