"""A/B testing framework for skills.

Runs two skill versions against the same benchmark queries and
promotes the higher-scoring version to active.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..types import SkillSpec, EvalScore


@dataclass(slots=True, frozen=True, kw_only=True)
class ABTestResult:
    """Result of an A/B test between two skill versions."""
    skill_name: str
    version_a: str
    version_b: str
    score_a: float
    score_b: float
    winner: str  # "a", "b", or "tie"
    delta: float
    queries_count: int


def run_ab_test(
    *,
    skill_a: SkillSpec,
    skill_b: SkillSpec,
    version_a: str,
    version_b: str,
    evaluator: Any,  # PipelineCore
    benchmark_queries: list[str],
    quality_threshold: float = 7.0,
) -> ABTestResult:
    """Run A/B test between two skill versions.

    Each skill is evaluated against the same benchmark queries.
    The higher-scoring version is the winner.
    """
    score_a_val = 0.0
    score_b_val = 0.0

    if hasattr(evaluator, 'evaluate_skill'):
        score_a = evaluator.evaluate_skill(skill=skill_a, benchmark_queries=benchmark_queries)
        score_b = evaluator.evaluate_skill(skill=skill_b, benchmark_queries=benchmark_queries)
        score_a_val = score_a.average if hasattr(score_a, 'average') else float(score_a)
        score_b_val = score_b.average if hasattr(score_b, 'average') else float(score_b)

    delta = score_b_val - score_a_val
    if abs(delta) < 0.1:
        winner = "tie"
    elif delta > 0:
        winner = "b"
    else:
        winner = "a"

    return ABTestResult(
        skill_name=skill_a.name,
        version_a=version_a,
        version_b=version_b,
        score_a=score_a_val,
        score_b=score_b_val,
        winner=winner,
        delta=abs(delta),
        queries_count=len(benchmark_queries),
    )


def promote_winner(
    *,
    result: ABTestResult,
    skill_a: SkillSpec,
    skill_b: SkillSpec,
    active_callback: Any | None = None,
) -> SkillSpec:
    """Promote the winning skill version. Returns the promoted skill."""
    if result.winner == "b":
        winner = skill_b
    else:
        winner = skill_a  # "a" or "tie" defaults to a

    if active_callback and callable(active_callback):
        active_callback(winner)

    return winner
