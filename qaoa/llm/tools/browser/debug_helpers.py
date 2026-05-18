# QAOA category: system, domain: technology
"""Lightweight debug utilities for migrated browser/web tools.

Kageko does not bundle the upstream debug module, so we provide a minimal
compatible API that the migrated ``web_utils.py`` expects.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _true_env(env_var: str) -> bool:
    v = os.getenv(env_var, "").strip().lower()
    return v in {"1", "true", "yes", "on"}


@dataclass
class DebugSession:
    tool_name: str
    env_var: str

    active: bool = field(init=False)
    session_id: str = field(init=False)
    log_dir: Path = field(init=False)
    _calls: List[Dict[str, Any]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.active = _true_env(self.env_var)
        self.session_id = uuid.uuid4().hex

        # Avoid coupling to Kageko's internal settings module; keep this
        # resilient when called early in process lifetime.
        base_dir = Path(os.getenv("KAAGEKO_HOME", Path.home() / ".kageko"))
        self.log_dir = base_dir / "logs"
        if self.active:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_call(self, name: str, payload: Dict[str, Any]) -> None:
        if not self.active:
            return
        self._calls.append(
            {
                "ts": time.time(),
                "tool": name,
                "payload": payload,
            }
        )

    def save(self) -> None:
        if not self.active:
            return
        out_path = self.log_dir / f"{self.tool_name}_debug_{self.session_id}.json"
        try:
            out_path.write_text(
                json.dumps(
                    {
                        "tool_name": self.tool_name,
                        "session_id": self.session_id,
                        "calls": self._calls,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            # Best-effort: debug should never break main flows.
            return

    def get_session_info(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "active": self.active,
            "session_id": self.session_id,
            "log_dir": str(self.log_dir),
        }
