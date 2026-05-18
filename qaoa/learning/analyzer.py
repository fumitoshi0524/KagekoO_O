# QAOA: analyze QAOA trajectories
from __future__ import annotations

import re
from collections import defaultdict

from .models import ClusterCandidate, EvolveType, Instinct


def normalize_trigger(trigger: str) -> str:
    t = (trigger or "").lower().strip()
    for token in ("when", "creating", "writing", "adding", "implementing", "testing"):
        t = t.replace(token, "")
    t = re.sub(r"\s+", " ", t).strip()
    return t or "general"


def infer_evolve_type(items: list[Instinct]) -> EvolveType:
    domains = {x.domain for x in items}
    if "workflow" in domains:
        return "command"
    if len(items) >= 4 and ("debugging" in domains or "research" in domains):
        return "agent"
    return "skill"


def build_clusters(
    instincts: list[Instinct],
    *,
    threshold: int = 3,
    domain: str = "",
    evolve_type: EvolveType | None = None,
    weighted_cluster_enabled: bool = False,
    weight_trigger: float = 1.0,
    weight_similarity: float = 0.0,
    weight_consistency: float = 0.0,
    instinct_experience_scores: dict[str, float] | None = None,
) -> list[ClusterCandidate]:
    grouped: dict[str, list[Instinct]] = defaultdict(list)
    for inst in instincts:
        if domain and inst.domain != domain:
            continue
        grouped[normalize_trigger(inst.trigger)].append(inst)
    out: list[ClusterCandidate] = []
    for key, rows in grouped.items():
        if len(rows) < threshold:
            continue
        et = infer_evolve_type(rows)
        if evolve_type and et != evolve_type:
            continue
        avg = sum(x.confidence for x in rows) / len(rows)
        exp_scores = [float((instinct_experience_scores or {}).get(x.id, 0.0)) for x in rows]
        exp_avg = sum(exp_scores) / max(1, len(exp_scores))
        confidence_consistency = 1.0 - min(1.0, max(0.0, (max(x.confidence for x in rows) - min(x.confidence for x in rows))))
        trigger_similarity = 1.0
        cluster_score = (
            (weight_trigger * trigger_similarity)
            + (weight_similarity * exp_avg)
            + (weight_consistency * confidence_consistency)
        ) if weighted_cluster_enabled else float(len(rows))
        out.append(
            ClusterCandidate(
                key=key,
                instincts=rows,
                avg_confidence=avg,
                domains=sorted({x.domain for x in rows}),
                evolve_type=et,
                cluster_score=round(cluster_score, 6),
                experience_score=round(exp_avg, 6),
            )
        )
    out.sort(
        key=lambda c: (
            -c.cluster_score if weighted_cluster_enabled else -len(c.instincts),
            -len(c.instincts),
            -c.avg_confidence,
            c.key,
        )
    )
    return out
