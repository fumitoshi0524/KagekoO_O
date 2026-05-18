from __future__ import annotations

from qaoa.skills.registry import SkillRegistry
from qaoa.types import SkillSpec


def make_skill(name, category="operations", domain="technology", tools=None):
    return SkillSpec(
        name=name, description=name, instructions=f"Step for {name}",
        allowed_tools=tools or ["file.read"], permissions=["read"],
        metadata={"category": category, "domain": domain},
        format="qaoa-uni-tool-call",
    )


def test_find_by_grid_exact_match():
    reg = SkillRegistry()
    reg.register(make_skill("data-analyzer", category="analysis", domain="science"))
    reg.register(make_skill("deployer", category="operations", domain="technology"))

    results = reg.find_by_grid(category="analysis", include_neighbors=False)
    assert len(results) == 1
    assert results[0].name == "data-analyzer"


def test_find_by_grid_with_neighbors():
    reg = SkillRegistry()
    reg.register(make_skill("a1", category="analysis", domain="science"))
    reg.register(make_skill("a2", category="analysis", domain="education"))
    reg.register(make_skill("o1", category="operations", domain="technology"))

    results = reg.find_by_grid(category="analysis", include_neighbors=True)
    assert len(results) >= 2


def test_classify_query_to_grid():
    reg = SkillRegistry()
    cat, dom = reg.classify_query_to_grid("analyze the science data and create a chart")
    assert cat == "analysis"
    assert dom == "science"


def test_classify_query_defaults():
    reg = SkillRegistry()
    cat, dom = reg.classify_query_to_grid("hello world")
    assert cat == "operations"
    assert dom == "technology"


def test_grid_distance():
    # analysis is index 0, operations is index 1
    d = SkillRegistry._grid_distance(
        target_cat="analysis", target_dom=None,
        skill_cat="analysis", skill_dom="technology",
    )
    assert d == 0  # same category, domain ignored since target_dom is None
