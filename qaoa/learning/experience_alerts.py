from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# QAOA: alert on trajectory degradation
from ..config.settings import Settings


def _cmp_threshold(value: float, cfg: dict[str, float | int]) -> tuple[str, str]:
    crit_lt = cfg.get("critical_lt")
    warn_lt = cfg.get("warning_lt")
    crit_gt = cfg.get("critical_gt")
    warn_gt = cfg.get("warning_gt")
    if isinstance(crit_lt, (int, float)) and value < float(crit_lt):
        return "critical", f"value<{crit_lt}"
    if isinstance(warn_lt, (int, float)) and value < float(warn_lt):
        return "warning", f"value<{warn_lt}"
    if isinstance(crit_gt, (int, float)) and value > float(crit_gt):
        return "critical", f"value>{crit_gt}"
    if isinstance(warn_gt, (int, float)) and value > float(warn_gt):
        return "warning", f"value>{warn_gt}"
    return "ok", ""


def evaluate_experience_alerts(settings: Settings, dashboard: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(getattr(settings.closed_loop, "experience_alert_thresholds", {}) or {})
    metrics = dict(dashboard.get("metrics", {}) or {})
    alerts: list[dict[str, Any]] = []
    max_level = "ok"
    for name, th in cfg.items():
        if name not in metrics:
            continue
        if not isinstance(th, dict):
            continue
        val = float(metrics.get(name, 0.0) or 0.0)
        level, reason = _cmp_threshold(val, th)  # static thresholds
        if name == "ecap_gap_convergence":
            wm = dashboard.get("window_metrics", {}) or {}
            keys = sorted([int(k) for k in wm.keys() if str(k).isdigit()])
            if len(keys) >= 2:
                short = float((wm.get(str(keys[0]), {}) or {}).get("ecap_gap_convergence", 0.0) or 0.0)
                long = float((wm.get(str(keys[-1]), {}) or {}).get("ecap_gap_convergence", 0.0) or 0.0)
                drop = max(0.0, long - short)
                if drop > float(th.get("critical_drop_gt", 999.0) or 999.0):
                    level, reason = "critical", f"drop>{th.get('critical_drop_gt')}"
                elif drop > float(th.get("warning_drop_gt", 999.0) or 999.0):
                    level, reason = "warning", f"drop>{th.get('warning_drop_gt')}"
        if level != "ok":
            alerts.append({"metric": name, "level": level, "value": round(val, 6), "reason": reason})
        if level == "critical":
            max_level = "critical"
        elif level == "warning" and max_level != "critical":
            max_level = "warning"

    out = {
        "schema_version": "experience-alerts-v1",
        "generated_at": datetime.now().isoformat(),
        "level": max_level,
        "alerts": alerts,
    }
    _write_alert_log(settings, out)
    return out


def _write_alert_log(settings: Settings, payload: dict[str, Any]) -> None:
    if not bool(getattr(settings.closed_loop, "experience_alert_enabled", True)):
        return
    root = settings.ensure_data_directory() / "learning" / "reports"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "experience_alerts.jsonl"
    cooldown = int(getattr(settings.closed_loop, "experience_alert_cooldown_minutes", 60) or 60)
    if path.exists():
        lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        if lines:
            try:
                last = json.loads(lines[-1])
                dt = datetime.fromisoformat(str(last.get("generated_at", "")))
                if datetime.now() - dt < timedelta(minutes=max(1, cooldown)):
                    return
            except Exception:
                pass
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
