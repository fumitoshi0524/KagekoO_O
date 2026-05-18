from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import get_settings


def evaluate_canary_promotion(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    min_improvement: float = 0.0,
) -> dict[str, Any]:
    """Compare baseline/candidate score and produce promote/hold decision."""
    b = float(baseline.get("score", 0.0) or 0.0)
    c = float(candidate.get("score", 0.0) or 0.0)
    delta = c - b
    decision = "promote" if delta >= float(min_improvement) else "hold"
    return {
        "decision": decision,
        "baseline_score": b,
        "candidate_score": c,
        "delta": delta,
        "reason": f"delta={delta:.4f}, min_improvement={min_improvement:.4f}",
    }


def run_canary_experiment(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    min_improvement: float = 0.0,
    min_samples: int = 5,
    min_confidence: float = 0.6,
    min_relative_improvement: float = 0.0,
    min_wilson_lower_bound: float = 0.0,
    control_ratio: float = 0.5,
    control_bucket: str = "default-control",
    candidate_bucket: str = "default-candidate",
    experiment_id: str | None = None,
) -> dict[str, Any]:
    """Run a lightweight canary lifecycle and persist result.

    States: draft -> running -> promoted/aborted
    """
    eid = experiment_id or f"canary-{uuid.uuid4().hex[:10]}"
    started = start_canary(
        experiment_id=eid,
        min_improvement=min_improvement,
        min_samples=min_samples,
        min_confidence=min_confidence,
        min_relative_improvement=min_relative_improvement,
        control_ratio=control_ratio,
        control_bucket=control_bucket,
        candidate_bucket=candidate_bucket,
    )
    base_score = float(baseline.get("score", 0.0) or 0.0)
    cand_score = float(candidate.get("score", 0.0) or 0.0)
    base_n = int(baseline.get("event_count", 0) or 0)
    cand_n = int(candidate.get("event_count", 0) or 0)
    delta = cand_score - base_score
    rel = (delta / abs(base_score)) if abs(base_score) > 1e-9 else delta
    enough_samples = min(base_n, cand_n) >= max(1, int(min_samples))
    result = evaluate_canary_promotion(
        baseline=baseline,
        candidate=candidate,
        min_improvement=min_improvement,
    )
    if not enough_samples:
        result["decision"] = "hold"
        result["reason"] = f"insufficient_samples baseline={base_n}, candidate={cand_n}, min={min_samples}"
    if result["decision"] == "promote" and rel < float(min_relative_improvement):
        result["decision"] = "hold"
        result["reason"] = f"relative_delta={rel:.4f} below min_relative_improvement={min_relative_improvement:.4f}"
    confidence = min(1.0, min(base_n, cand_n) / max(1.0, float(min_samples)))
    win_rate = max(0.0, min(1.0, cand_score))
    wilson_lb = _wilson_lower_bound(win_rate, cand_n)
    if result["decision"] == "promote" and confidence < float(min_confidence):
        result["decision"] = "hold"
        result["reason"] = f"confidence={confidence:.4f} below min_confidence={min_confidence:.4f}"
    if result["decision"] == "promote" and wilson_lb < float(min_wilson_lower_bound):
        result["decision"] = "hold"
        result["reason"] = f"wilson_lb={wilson_lb:.4f} below min_wilson_lower_bound={min_wilson_lower_bound:.4f}"
    final_state = "promoted" if result["decision"] == "promote" else "aborted"
    checkpoint = tick_canary(
        experiment_id=eid,
        baseline_samples=base_n,
        candidate_samples=cand_n,
        confidence=confidence,
        absolute_delta=delta,
        relative_delta=rel,
    )
    payload = {
        "experiment_id": eid,
        "state": final_state,
        "lifecycle": ["draft", "running", final_state],
        "baseline_score": base_score,
        "candidate_score": cand_score,
        "baseline_samples": base_n,
        "candidate_samples": cand_n,
        "absolute_delta": delta,
        "relative_delta": rel,
        "confidence": round(confidence, 4),
        "decision": result["decision"],
        "reason": result.get("reason", ""),
        "min_improvement": float(min_improvement),
        "min_samples": int(min_samples),
        "min_confidence": float(min_confidence),
        "min_relative_improvement": float(min_relative_improvement),
        "min_wilson_lower_bound": float(min_wilson_lower_bound),
        "control_ratio": max(0.0, min(1.0, float(control_ratio))),
        "candidate_ratio": round(1.0 - max(0.0, min(1.0, float(control_ratio))), 4),
        "control_bucket": str(control_bucket),
        "candidate_bucket": str(candidate_bucket),
        "wilson_lower_bound": round(wilson_lb, 6),
        "evaluated_at_ts": int(time.time()),
    }
    payload["phase"] = final_state
    payload["termination_reason"] = result.get("reason", "")
    payload["checkpoint_count"] = int(checkpoint.get("checkpoint_count", 1))
    payload["report_ref"] = _append_canary_result(payload)
    stop_canary(experiment_id=eid, final_state=final_state, reason=payload["termination_reason"], report_ref=payload["report_ref"])
    return payload


def start_canary(
    *,
    experiment_id: str,
    min_improvement: float,
    min_samples: int,
    min_confidence: float,
    min_relative_improvement: float,
    control_ratio: float,
    control_bucket: str = "default-control",
    candidate_bucket: str = "default-candidate",
) -> dict[str, Any]:
    row = {
        "event": "start",
        "experiment_id": experiment_id,
        "state": "running",
        "evaluated_at_ts": int(time.time()),
        "min_improvement": float(min_improvement),
        "min_samples": int(min_samples),
        "min_confidence": float(min_confidence),
        "min_relative_improvement": float(min_relative_improvement),
        "control_ratio": max(0.0, min(1.0, float(control_ratio))),
        "control_bucket": str(control_bucket),
        "candidate_bucket": str(candidate_bucket),
    }
    _append_canary_result(row)
    return row


def tick_canary(
    *,
    experiment_id: str,
    baseline_samples: int,
    candidate_samples: int,
    confidence: float,
    absolute_delta: float,
    relative_delta: float,
) -> dict[str, Any]:
    row = {
        "event": "tick",
        "experiment_id": experiment_id,
        "state": "running",
        "baseline_samples": int(baseline_samples),
        "candidate_samples": int(candidate_samples),
        "confidence": round(float(confidence), 4),
        "absolute_delta": float(absolute_delta),
        "relative_delta": float(relative_delta),
        "checkpoint_count": 1,
        "evaluated_at_ts": int(time.time()),
    }
    _append_canary_result(row)
    return row


def stop_canary(*, experiment_id: str, final_state: str, reason: str, report_ref: str) -> dict[str, Any]:
    row = {
        "event": "stop",
        "experiment_id": experiment_id,
        "state": str(final_state),
        "terminal_reason": str(reason),
        "report_ref": str(report_ref),
        "evaluated_at_ts": int(time.time()),
    }
    _append_canary_result(row)
    return row


def _append_canary_result(payload: dict[str, Any]) -> str:
    try:
        settings = get_settings()
        p = (settings.ensure_data_directory() / "qaoa_metrics" / "canary_results.jsonl").resolve()
    except Exception:
        p = (Path.cwd() / ".qaoa" / "qaoa_metrics" / "canary_results.jsonl").resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return str(p)


def _wilson_lower_bound(p: float, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = max(0.0, min(1.0, float(p)))
    denom = 1.0 + (z * z) / n
    center = p + (z * z) / (2.0 * n)
    margin = z * (((p * (1.0 - p)) / n + (z * z) / (4.0 * n * n)) ** 0.5)
    return max(0.0, min(1.0, (center - margin) / denom))
