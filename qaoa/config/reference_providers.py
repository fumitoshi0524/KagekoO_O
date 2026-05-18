"""Default provider ``models`` lists for the TUI model picker (empty slot in user config).

When a provider entry has no ``models`` array, we fill candidates from the same keys as in
the project ``.kageko.json`` catalog: prefer the repo/adjacent ``.kageko.json`` when
present, otherwise the bundled ``reference_providers.json`` (models only, no secrets).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _parse_providers_models(raw: dict[str, Any]) -> dict[str, list[str]]:
    providers = raw.get("providers") or {}
    out: dict[str, list[str]] = {}
    for key, val in providers.items():
        if not isinstance(val, dict):
            continue
        models = val.get("models")
        if isinstance(models, list):
            out[key] = [str(m) for m in models if m]
        else:
            out[key] = []
    return out


@lru_cache
def _reference_provider_models_map() -> dict[str, list[str]]:
    config_dir = Path(__file__).resolve().parent
    # Repo / editable layout: qaoa/.kageko.json (two levels above this package subdir)
    kageko_json = config_dir.parents[2] / ".kageko.json"
    for path in (kageko_json, config_dir / "reference_providers.json"):
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        models_map = _parse_providers_models(raw)
        if models_map:
            return models_map
    return {}


def provider_models_from_reference(provider_key: str) -> list[str]:
    """Return model ids for ``provider_key`` from the reference catalog (copy of .kageko.json)."""
    return list(_reference_provider_models_map().get(provider_key, []))
