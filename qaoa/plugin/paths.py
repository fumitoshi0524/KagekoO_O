"""Resolve plugin filesystem layout (Claude Code compatible)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config.settings import Settings
from ..storage_paths import ensure_primary_root


@dataclass(frozen=True)
class PluginPaths:
    """Layout under plugin data root (e.g. ~/.kageko or ~/.claude)."""

    data_root: Path
    user_plugins_dir: Path
    cache_dir: Path
    marketplaces_dir: Path
    state_file: Path


def resolve_plugin_paths(settings: Settings) -> PluginPaths:
    """Compute plugin directories from ``settings.plugins``."""
    mode = settings.plugins.data_root_mode
    if mode == "claude":
        root = Path.home() / ".claude"
    elif mode == "custom":
        raw = settings.plugins.plugins_data_root
        root = Path(raw).expanduser().resolve() if raw else Path.home() / ".kageko"
    else:
        # Default local storage is .kageko
        wd = str(getattr(settings, "working_directory", "") or "").strip()
        root = ensure_primary_root(wd or Path.cwd())

    root.mkdir(parents=True, exist_ok=True)
    plugins = root / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    cache = plugins / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    mdir = root / "marketplaces"
    mdir.mkdir(parents=True, exist_ok=True)

    return PluginPaths(
        data_root=root,
        user_plugins_dir=plugins,
        cache_dir=cache,
        marketplaces_dir=mdir,
        state_file=root / "plugin-state.json",
    )
