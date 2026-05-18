from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# QAOA: metrics for QAOA turns
from ..config.settings import Settings
from .experience_store import list_capsules
from .team_experience_store import list_team_capsules


def _now() -> datetime:
    return datetime.now()


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


def _window_rows(rows: list[Any], *, days: int, ts_getter) -> list[Any]:
    cutoff = _now() - timedelta(days=max(1, int(days)))
    out: list[Any] = []
    for one in rows:
        dt = ts_getter(one)
        if dt is None:
            continue
        if dt >= cutoff:
            out.append(one)
    return out


def _window_stats(settings: Settings, days: int, min_samples: int, *, domain: str | None = None) -> dict[str, float]:
    caps = _window_rows(
        list_capsules(settings),
        days=days,
        ts_getter=lambda c: _parse_iso(c.governance.updated_at or c.governance.created_at),
    )
    if domain:
        caps = [x for x in caps if str(x.problem_type or "").strip().lower() == str(domain).strip().lower()]
    if not caps:
        return {
            "ecap_effectiveness_avg": 0.0,
            "ecap_confidence_avg": 0.0,
            "ecap_ci_width_avg": 1.0,
            "ecap_sample_sufficiency_rate": 0.0,
            "ecap_gap_convergence": 0.0,
            "routing_experience_contribution": 0.0,
        }
    score = [float(x.knowledge_triple.experience_fn.score or 0.0) for x in caps]
    conf = [float(x.knowledge_triple.experience_fn.confidence or 0.0) for x in caps]
    width = [
        max(
            0.0,
            float(x.knowledge_triple.experience_fn.ci_upper or 1.0) - float(x.knowledge_triple.experience_fn.ci_lower or 0.0),
        )
        for x in caps
    ]
    gap = [float(x.knowledge_triple.experience_fn.gap or 1.0) for x in caps]
    suff = [1.0 if int(x.knowledge_triple.experience_fn.sample_count or 0) >= int(min_samples) else 0.0 for x in caps]
    contrib = []
    for x in caps:
        rx = x.model_profile.capability_profile.get("routing_explain", {}) if isinstance(x.model_profile.capability_profile, dict) else {}
        if not isinstance(rx, dict):
            continue
        exp_num = float(rx.get("experience_score", 0.0) or 0.0) + float(rx.get("confidence", 0.0) or 0.0)
        denom = exp_num + float(rx.get("risk_gap", 0.0) or 0.0) + float(rx.get("quality_gap", 0.0) or 0.0) + 1e-9
        contrib.append(max(0.0, min(1.0, exp_num / denom)))
    return {
        "ecap_effectiveness_avg": round(sum(score) / max(1, len(score)), 6),
        "ecap_confidence_avg": round(sum(conf) / max(1, len(conf)), 6),
        "ecap_ci_width_avg": round(sum(width) / max(1, len(width)), 6),
        "ecap_sample_sufficiency_rate": round(sum(suff) / max(1, len(suff)), 6),
        "ecap_gap_convergence": round(max(0.0, min(1.0, 1.0 - (sum(gap) / max(1, len(gap))))), 6),
        "routing_experience_contribution": round(sum(contrib) / max(1, len(contrib)), 6) if contrib else 0.0,
    }


def build_experience_dashboard(settings: Settings, *, domain: str | None = None) -> dict[str, Any]:
    cl = settings.closed_loop
    windows = list(getattr(cl, "experience_dashboard_window_days", [7, 30, 90]) or [7, 30, 90])
    windows = [int(x) for x in windows if int(x) > 0]
    windows = windows or [7, 30, 90]
    min_samples = int(getattr(cl, "experience_dashboard_min_samples", 3) or 3)

    per_window = {str(d): _window_stats(settings, d, min_samples, domain=domain) for d in windows}
    current = per_window[str(min(windows))]

    instinct_delta_log = settings.ensure_data_directory() / "learning" / "experience" / "instinct_delta.jsonl"
    instinct_rows = _load_jsonl(instinct_delta_log)
    instinct_delta_net = round(sum(float(x.get("delta", 0.0) or 0.0) for x in instinct_rows[-500:]), 6)

    snapshot_dir = settings.ensure_data_directory() / "learning" / "snapshots"
    gate_rows: list[dict[str, Any]] = []
    if snapshot_dir.exists():
        for f in sorted(snapshot_dir.glob("*autonomous-cycle*.json"))[-120:]:
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            res = (obj.get("payload") or {}).get("result") if isinstance(obj, dict) else None
            if isinstance(res, dict):
                gate_rows.append(res)
    total_candidates = 0
    total_gated = 0
    tuning_gate_pass = 0
    for row in gate_rows:
        ip = row.get("import_payload", {}) or {}
        sm = ip.get("summary", {}) if isinstance(ip, dict) else {}
        if isinstance(sm, dict):
            cand = int(sm.get("created", 0) or 0) + int(sm.get("updated", 0) or 0) + int(sm.get("skipped_same_content", 0) or 0)
            cand += int(sm.get("conflicts", 0) or 0) + int(sm.get("gated_by_experience_count", 0) or 0)
            total_candidates += cand
            total_gated += int(sm.get("gated_by_experience_count", 0) or 0)
        eg = row.get("experience_tuning_gate", {}) or {}
        if bool(eg.get("allowed", False)):
            tuning_gate_pass += 1
    experience_gate_block_rate = round(float(total_gated) / max(1, float(total_candidates)), 6)
    tuning_experience_gate_pass_rate = round(float(tuning_gate_pass) / max(1, float(len(gate_rows))), 6)

    # closed-loop gain consistency: same-direction ratio between short/long convergence and long-term trend
    trend_rows = [x for x in gate_rows if isinstance(x.get("long_term_metrics", {}), dict)]
    if domain:
        d = str(domain).strip().lower()
        trend_rows = [x for x in trend_rows if str(x.get("domain", "") or "").strip().lower() == d]
    same_dir = 0
    for row in trend_rows:
        lt = row.get("long_term_metrics", {}) or {}
        w7 = float((((lt.get("windows", {}) or {}).get("7", {}) or {}).get("normalized_combined_score", 0.0) or 0.0))
        w90 = float((((lt.get("windows", {}) or {}).get("90", {}) or {}).get("normalized_combined_score", 0.0) or 0.0))
        improve_lt = (w7 - w90) >= 0.0
        improve_gap = current["ecap_gap_convergence"] >= per_window[str(max(windows))]["ecap_gap_convergence"]
        if improve_lt == improve_gap:
            same_dir += 1
    closed_loop_gain_consistency = round(float(same_dir) / max(1, float(len(trend_rows))), 6)
    ab_comparison: dict[str, Any] = {"enabled": False, "buckets": {}, "delta": 0.0}
    if bool(getattr(cl, "experience_ab_enabled", True)):
        domain_rows: dict[str, list[float]] = {}
        allow_domains = [str(x).strip().lower() for x in list(getattr(cl, "experience_ab_domains", []) or []) if str(x).strip()]
        for row in trend_rows:
            dom = str(row.get("domain", "") or "general").strip().lower() or "general"
            if allow_domains and dom not in allow_domains:
                continue
            lt = row.get("long_term_metrics", {}) or {}
            w7 = float((((lt.get("windows", {}) or {}).get("7", {}) or {}).get("normalized_combined_score", 0.0) or 0.0))
            domain_rows.setdefault(dom, []).append(w7)
        buckets = {k: round(sum(v) / max(1, len(v)), 6) for k, v in domain_rows.items() if v}
        if buckets:
            vals = sorted(buckets.values())
            sample_size = int(sum(len(v) for v in domain_rows.values()))
            confidence = round(max(0.0, min(1.0, sample_size / 30.0)), 6)
            ab_comparison = {
                "enabled": True,
                "experiment_id": f"exp-{_now().strftime('%Y%m%d')}",
                "sample_size": sample_size,
                "buckets": buckets,
                "delta": round(vals[-1] - vals[0], 6),
                "confidence": confidence,
                "is_significant": bool(sample_size >= 10 and abs(vals[-1] - vals[0]) >= 0.05),
            }

    metrics = {
        **current,
        "instinct_delta_net": instinct_delta_net,
        "experience_gate_block_rate": experience_gate_block_rate,
        "tuning_experience_gate_pass_rate": tuning_experience_gate_pass_rate,
        "closed_loop_gain_consistency": closed_loop_gain_consistency,
    }

    return {
        "schema_version": "experience-dashboard-v1",
        "generated_at": _now().isoformat(),
        "domain": str(domain or ""),
        "windows_days": windows,
        "metrics": metrics,
        "window_metrics": per_window,
        "scope_metrics": {
            "model": {"routing_experience_contribution": current.get("routing_experience_contribution", 0.0)},
            "agent": {"routing_experience_contribution": current.get("routing_experience_contribution", 0.0)},
            "skill": {"routing_experience_contribution": current.get("routing_experience_contribution", 0.0)},
            "team": {
                "tecap_count": len(
                    [
                        x
                        for x in list_team_capsules(settings)
                        if (not domain) or str(x.problem_type or "").strip().lower() == str(domain).strip().lower()
                    ]
                ),
                "avg_score": round(
                    sum(
                        float(x.team_experience_fn.score or 0.0)
                        for x in list_team_capsules(settings)
                        if (not domain) or str(x.problem_type or "").strip().lower() == str(domain).strip().lower()
                    )
                    / max(
                        1,
                        len(
                            [
                                x
                                for x in list_team_capsules(settings)
                                if (not domain) or str(x.problem_type or "").strip().lower() == str(domain).strip().lower()
                            ]
                        ),
                    ),
                    6,
                )
                if list_team_capsules(settings)
                else 0.0,
            },
        },
        "ab_comparison": ab_comparison,
    }
