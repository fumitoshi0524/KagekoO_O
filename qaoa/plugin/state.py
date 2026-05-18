"""Persistent plugin + marketplace state (plugin-state.json)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class MarketplaceRecord(BaseModel):
    """Registered marketplace checkout or path."""

    model_config = ConfigDict(extra="ignore")

    name: str
    source: str
    local_path: str


class InstalledPluginRecord(BaseModel):
    """Plugin installed from a marketplace (lives under plugins/cache)."""

    model_config = ConfigDict(extra="ignore")

    marketplace: str
    cache_subdir: str
    enabled: bool = True


class PluginState(BaseModel):
    """Top-level state file schema."""

    model_config = ConfigDict(extra="ignore")

    version: int = 1
    marketplaces: dict[str, MarketplaceRecord] = Field(default_factory=dict)
    installed: dict[str, InstalledPluginRecord] = Field(default_factory=dict)


def load_plugin_state(path: Path) -> PluginState:
    if not path.exists():
        return PluginState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(raw, dict):
            return PluginState()
        return PluginState.model_validate(raw)
    except Exception as e:
        logger.warning("Failed to load plugin state %s: %s", path, e)
        return PluginState()


def save_plugin_state(path: Path, state: PluginState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = state.model_dump(mode="json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
