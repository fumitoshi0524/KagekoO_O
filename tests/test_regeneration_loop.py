from __future__ import annotations

from qaoa.types import SkillSpec, EvalScore, RegenerationFeedback
from qaoa.skills.conformance import ConformanceEngine


def test_regeneration_triggered_when_eval_fails():
    feedback = RegenerationFeedback(
        query="analyze data",
        expected_tools=["file.read", "bash.run"],
        observed_tools=["echo"],
        eval_score=EvalScore(toolfit=4.0, clarity=3.0, naturalness=5.0),
        suggestions="Add more specific steps and tool bindings",
    )
    assert feedback.eval_score.passes(threshold=7.0) is False
    assert feedback.eval_score.average == 4.0


def test_skill_passes_when_eval_succeeds():
    skill = SkillSpec(
        name="strong-skill",
        description="Well structured",
        instructions="1. Read input\n2. Process data\n3. Write output\n4. Report results",
        allowed_tools=["file.read", "file.write"],
        permissions=["read", "write"],
        metadata={"category": "operations", "domain": "technology"},
        format="qaoa-uni-tool-call",
    )
    engine = ConformanceEngine()
    result = engine.validate(skill)
    assert result.passed is True


def test_conformance_and_eval_pipeline():
    engine = ConformanceEngine()
    skill = SkillSpec(
        name="pipeline-test",
        description="End to end pipeline",
        instructions="1. Read the data\n2. Analyze findings\n3. Generate report\n4. Answer user",
        allowed_tools=["file.read", "file.write", "bash.run"],
        permissions=["read", "write"],
        metadata={"category": "analysis", "domain": "science"},
        format="qaoa-uni-tool-call",
    )
    conformance = engine.validate(skill)
    assert conformance.passed, f"Conformance failed: {conformance.issues}"
