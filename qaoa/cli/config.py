"""Global config load/save — single source of truth for Kageko configuration."""

from __future__ import annotations

import json
from pathlib import Path


def get_config_path() -> Path:
    return Path.home() / ".kageko" / "config.json"


def load_global_config() -> dict[str, object]:
    path = get_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_global_config(config: dict[str, object]) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
