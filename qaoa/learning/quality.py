# QAOA: evaluate trajectory quality
from __future__ import annotations

from datetime import datetime, timezone


def _parse_ts(ts: str) -> datetime | None:
    t = (ts or "").strip()
    if not t:
        return None
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except Exception:
        return None


def apply_confidence_decay(
    confidence: float,
    *,
    updated_at: str,
    decay_rate: float = 0.03,
    min_floor: float = 0.2,
) -> float:
    dt = _parse_ts(updated_at)
    if dt is None:
        return max(min_floor, min(1.0, confidence))
    now = datetime.now(timezone.utc)
    days = max(0.0, (now - dt).total_seconds() / 86400.0)
    decayed = confidence * ((1.0 - decay_rate) ** days)
    return max(min_floor, min(1.0, decayed))


def update_confidence(
    current: float,
    *,
    success_count: int = 0,
    failure_count: int = 0,
    step: float = 0.04,
    min_floor: float = 0.2,
) -> float:
    out = current + (success_count * step) - (failure_count * step * 1.2)
    return max(min_floor, min(1.0, out))
