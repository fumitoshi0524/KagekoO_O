from __future__ import annotations

from qaoa.types import ConformanceResult, EvalScore


def test_conformance_result_defaults():
    result = ConformanceResult(passed=False, reason="missing category")
    assert result.passed is False
    assert result.reason == "missing category"
    assert result.issues == []
    assert result.score == 0.0


def test_conformance_result_with_issues():
    result = ConformanceResult(
        passed=False,
        reason="multiple issues",
        issues=["no domain assigned", "tool 'missing.tool' not found"],
        score=0.3,
    )
    assert len(result.issues) == 2
    assert result.score == 0.3


def test_eval_score_threshold():
    score = EvalScore(toolfit=8.0, clarity=7.5, naturalness=9.0)
    assert score.average == 8.166666666666666
    assert score.passes(threshold=7.0) is True
    assert score.passes(threshold=8.5) is False


from qaoa.skills.conformance import ConformanceEngine
from qaoa.types import SkillSpec


def test_conformance_passes_valid_skill():
    engine = ConformanceEngine()
    skill = SkillSpec(
        name="data-analyzer",
        description="Analyze data files and produce reports",
        instructions="1. Read the data file\n2. Analyze contents\n3. Generate report\n4. Answer with findings",
        allowed_tools=["file.read", "file.write", "bash.run"],
        permissions=["read", "write"],
        metadata={"category": "analysis", "domain": "science"},
        format="qaoa-uni-tool-call",
    )
    result = engine.validate(skill)
    assert result.passed is True
    assert result.score >= 0.7


def test_conformance_rejects_missing_category():
    engine = ConformanceEngine()
    skill = SkillSpec(
        name="bad-skill",
        description="Does stuff",
        instructions="Just do it",
        allowed_tools=["echo"],
        permissions=[],
        metadata={},
        format="qaoa-uni-tool-call",
    )
    result = engine.validate(skill)
    assert result.passed is False
    assert any("category" in issue.lower() or "domain" in issue.lower() for issue in result.issues)


def test_conformance_rejects_no_instructions():
    engine = ConformanceEngine()
    skill = SkillSpec(
        name="empty-skill",
        description="Has metadata but no body",
        instructions="",
        allowed_tools=["echo"],
        permissions=["read"],
        metadata={"category": "system", "domain": "technology"},
        format="qaoa-uni-tool-call",
    )
    result = engine.validate(skill)
    assert result.passed is False
    assert any("instruction" in issue.lower() for issue in result.issues)
