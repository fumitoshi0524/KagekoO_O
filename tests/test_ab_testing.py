from __future__ import annotations

from qaoa.experience.ab_testing import ABTestResult, promote_winner
from qaoa.types import SkillSpec


def test_ab_result_winner_b():
    result = ABTestResult(
        skill_name="test", version_a="v1", version_b="v2",
        score_a=7.5, score_b=8.5, winner="b", delta=1.0, queries_count=3,
    )
    assert result.winner == "b"
    assert result.delta == 1.0


def test_ab_result_tie():
    result = ABTestResult(
        skill_name="test", version_a="v1", version_b="v2",
        score_a=8.0, score_b=8.0, winner="tie", delta=0.0, queries_count=3,
    )
    assert result.winner == "tie"


def test_promote_winner_b():
    skill_a = SkillSpec(
        name="v1", description="old", instructions="step 1",
        allowed_tools=["file.read"], permissions=["read"],
        metadata={}, format="test",
    )
    skill_b = SkillSpec(
        name="v2", description="new", instructions="step 1\nstep 2",
        allowed_tools=["file.read", "file.write"], permissions=["read", "write"],
        metadata={}, format="test",
    )
    result = ABTestResult(
        skill_name="test", version_a="v1", version_b="v2",
        score_a=6.0, score_b=9.0, winner="b", delta=3.0, queries_count=2,
    )
    winner = promote_winner(result=result, skill_a=skill_a, skill_b=skill_b)
    assert winner.name == "v2"


def test_promote_winner_a_when_tie():
    skill_a = SkillSpec(
        name="v1", description="a", instructions="s1",
        allowed_tools=[], permissions=[], metadata={}, format="test",
    )
    skill_b = SkillSpec(
        name="v2", description="b", instructions="s2",
        allowed_tools=[], permissions=[], metadata={}, format="test",
    )
    result = ABTestResult(
        skill_name="test", version_a="v1", version_b="v2",
        score_a=7.0, score_b=7.0, winner="tie", delta=0.0, queries_count=1,
    )
    winner = promote_winner(result=result, skill_a=skill_a, skill_b=skill_b)
    assert winner.name == "v1"  # ties default to a
