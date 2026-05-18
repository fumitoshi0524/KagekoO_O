from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# QAOA: observe QAOA turns
from .paths import LearningPaths


@dataclass
class ObserverState:
    checkpoint_line: int = 0
    last_run: str = ""
    processed_count: int = 0


def _state_file(paths: LearningPaths) -> Path:
    return paths.root / "observer-state.json"


def load_observer_state(paths: LearningPaths) -> ObserverState:
    f = _state_file(paths)
    if not f.exists():
        return ObserverState()
    try:
        obj = json.loads(f.read_text(encoding="utf-8"))
        return ObserverState(
            checkpoint_line=int(obj.get("checkpoint_line", 0)),
            last_run=str(obj.get("last_run", "")),
            processed_count=int(obj.get("processed_count", 0)),
        )
    except Exception:
        return ObserverState()


def save_observer_state(paths: LearningPaths, st: ObserverState) -> None:
    f = _state_file(paths)
    f.write_text(
        json.dumps(
            {
                "checkpoint_line": st.checkpoint_line,
                "last_run": st.last_run,
                "processed_count": st.processed_count,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def consume_new_observations(paths: LearningPaths, *, max_rows: int = 500) -> tuple[list[dict], ObserverState]:
    st = load_observer_state(paths)
    if not paths.observations_file.exists():
        return [], st
    lines = paths.observations_file.read_text(encoding="utf-8").splitlines()
    start = max(0, st.checkpoint_line)
    chunk = lines[start : start + max_rows]
    out: list[dict] = []
    for one in chunk:
        try:
            obj = json.loads(one)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    st.checkpoint_line = start + len(chunk)
    st.processed_count += len(out)
    st.last_run = datetime.now(timezone.utc).isoformat()
    save_observer_state(paths, st)
    return out, st
