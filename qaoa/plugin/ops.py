"""Marketplace registration, plugin install/uninstall (shared by CLI and /plugin)."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from ..config.settings import Settings
from .fetch import FetchError, fetch_plugin_source, stable_cache_subdir

__all__ = [
    "FetchError",
    "install_plugin_from_marketplace",
    "install_plugin_local_path",
    "marketplace_add",
    "marketplace_list",
    "marketplace_remove",
    "marketplace_update",
    "set_plugin_enabled",
    "uninstall_plugin",
]
from .marketplace_catalog import (
    find_plugin_entry,
    load_marketplace_from_root,
    marketplace_json_path,
    plugin_root_prefix,
)
from .paths import resolve_plugin_paths
from .state import InstalledPluginRecord, MarketplaceRecord, PluginState, load_plugin_state, save_plugin_state

logger = logging.getLogger(__name__)


def _slug(s: str) -> str:
    x = re.sub(r"[^a-zA-Z0-9_.-]+", "-", s.strip()).strip("-")
    return x[:64] or "marketplace"


def _materialize_marketplace_source(source: str, marketplaces_dir: Path) -> tuple[Path, str]:
    """Return (marketplace_root_dir, original_source_string)."""
    s = source.strip().strip('"').strip("'")
    p = Path(s).expanduser()

    if p.is_dir():
        mp = marketplace_json_path(p)
        if not mp.is_file():
            raise FetchError(f"No .claude-plugin/marketplace.json under {p}")
        return p.resolve(), s

    if p.is_file() and p.name == "marketplace.json":
        root = p.parent.parent
        if root.name != ".claude-plugin":
            raise FetchError("marketplace.json must live under .claude-plugin/")
        return root.parent.resolve(), s

    if s.startswith("http://") or s.startswith("https://"):
        req = urllib.request.Request(s, headers={"User-Agent": "Kageko/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
        try:
            meta = json.loads(body.decode("utf-8", errors="replace"))
            mkey = _slug(str(meta.get("name") or s.split("/")[-1].replace(".json", "") or "remote"))
        except Exception:
            mkey = _slug(s.split("/")[-1].replace(".json", "") or "remote")
        dest_root = marketplaces_dir / mkey
        if dest_root.exists():
            shutil.rmtree(dest_root, ignore_errors=True)
        dest_root.mkdir(parents=True, exist_ok=True)
        plug = dest_root / ".claude-plugin"
        plug.mkdir(parents=True, exist_ok=True)
        (plug / "marketplace.json").write_bytes(body)
        return dest_root.resolve(), s

    # Treat as git URL or github shorthand
    url = s
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", s):
        url = f"https://github.com/{s}.git"
    dest = marketplaces_dir / _slug(s.replace(":", "/").replace("/", "-"))
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise FetchError("git is required to clone this marketplace") from e
    except subprocess.CalledProcessError as e:
        raise FetchError((e.stderr or e.stdout or str(e)).strip()) from e
    mp = marketplace_json_path(dest)
    if not mp.is_file():
        shutil.rmtree(dest, ignore_errors=True)
        raise FetchError(f"Cloned repo has no .claude-plugin/marketplace.json: {dest}")
    return dest.resolve(), s


def marketplace_add(settings: Settings, source: str) -> tuple[str, Path]:
    paths = resolve_plugin_paths(settings)
    paths.marketplaces_dir.mkdir(parents=True, exist_ok=True)
    root, src = _materialize_marketplace_source(source, paths.marketplaces_dir)
    cat = load_marketplace_from_root(root)
    if cat is None:
        raise FetchError("Invalid marketplace catalog")
    name = cat.name
    state = load_plugin_state(paths.state_file)
    state.marketplaces[name] = MarketplaceRecord(name=name, source=src, local_path=str(root))
    save_plugin_state(paths.state_file, state)
    return name, root


def marketplace_list(settings: Settings) -> list[MarketplaceRecord]:
    paths = resolve_plugin_paths(settings)
    state = load_plugin_state(paths.state_file)
    return list(state.marketplaces.values())


def _is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def marketplace_remove(settings: Settings, name: str) -> bool:
    paths = resolve_plugin_paths(settings)
    state = load_plugin_state(paths.state_file)
    if name not in state.marketplaces:
        return False
    rec = state.marketplaces.pop(name)
    save_plugin_state(paths.state_file, state)
    lp = Path(rec.local_path)
    if lp.is_dir() and _is_under(lp, paths.marketplaces_dir):
        shutil.rmtree(lp, ignore_errors=True)
    return True


def marketplace_update(settings: Settings, name: str | None = None) -> list[str]:
    paths = resolve_plugin_paths(settings)
    state = load_plugin_state(paths.state_file)
    updated: list[str] = []
    targets = [name] if name is not None else list(state.marketplaces.keys())
    for mname in targets:
        if mname not in state.marketplaces:
            continue
        rec = state.marketplaces[mname]
        root = Path(rec.local_path)
        git_dir = root / ".git"
        if git_dir.is_dir():
            try:
                subprocess.run(
                    ["git", "-C", str(root), "pull", "--ff-only"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                updated.append(mname)
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                logger.warning("git pull failed for %s: %s", mname, e)
            continue
        src = rec.source
        if src.startswith("http://") or src.startswith("https://"):
            req = urllib.request.Request(src, headers={"User-Agent": "Kageko/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
            plug = root / ".claude-plugin"
            plug.mkdir(parents=True, exist_ok=True)
            (plug / "marketplace.json").write_bytes(body)
            updated.append(mname)
    save_plugin_state(paths.state_file, state)
    return updated


def install_plugin_from_marketplace(
    settings: Settings,
    plugin_name: str,
    marketplace_name: str,
) -> Path:
    paths = resolve_plugin_paths(settings)
    state = load_plugin_state(paths.state_file)
    if marketplace_name not in state.marketplaces:
        raise FetchError(f"Unknown marketplace: {marketplace_name}")
    mrec = state.marketplaces[marketplace_name]
    root = Path(mrec.local_path)
    cat = load_marketplace_from_root(root)
    if cat is None:
        raise FetchError("Marketplace catalog missing or invalid")
    entry = find_plugin_entry(cat, plugin_name)
    if entry is None:
        raise FetchError(f"Plugin {plugin_name!r} not found in marketplace {marketplace_name!r}")
    src = entry.get("source")
    if src is None:
        raise FetchError("Plugin entry has no source")
    pr = plugin_root_prefix(cat)
    fp = json_fingerprint(entry, src)
    subdir = stable_cache_subdir(plugin_name, fp)
    dest = paths.cache_dir / subdir
    fetch_plugin_source(
        source=src,
        dest=dest,
        marketplace_root=root,
        plugin_root_prefix=pr,
    )
    state.installed[plugin_name] = InstalledPluginRecord(
        marketplace=marketplace_name,
        cache_subdir=subdir,
        enabled=True,
    )
    save_plugin_state(paths.state_file, state)
    return dest


def json_fingerprint(entry: dict[str, Any], source: Any) -> str:
    try:
        return json.dumps({"source": source, "entry": entry}, sort_keys=True, default=str)
    except Exception:
        return repr(source) + repr(entry)


def uninstall_plugin(settings: Settings, plugin_name: str) -> bool:
    paths = resolve_plugin_paths(settings)
    state = load_plugin_state(paths.state_file)
    if plugin_name not in state.installed:
        return False
    rec = state.installed.pop(plugin_name)
    save_plugin_state(paths.state_file, state)
    target = paths.cache_dir / rec.cache_subdir
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
    return True


def set_plugin_enabled(settings: Settings, plugin_name: str, enabled: bool) -> bool:
    paths = resolve_plugin_paths(settings)
    state = load_plugin_state(paths.state_file)
    if plugin_name not in state.installed:
        return False
    r = state.installed[plugin_name]
    state.installed[plugin_name] = InstalledPluginRecord(
        marketplace=r.marketplace,
        cache_subdir=r.cache_subdir,
        enabled=enabled,
    )
    save_plugin_state(paths.state_file, state)
    return True


def install_plugin_local_path(settings: Settings, source_dir: Path) -> tuple[str, Path]:
    """Copy a local plugin tree into cache and register as installed from 'local'."""
    from .loader import load_plugin_from_dir

    paths = resolve_plugin_paths(settings)
    if not source_dir.is_dir():
        raise FetchError(f"Not a directory: {source_dir}")
    temp = load_plugin_from_dir(source_dir)
    if temp is None:
        raise FetchError("Not a valid plugin directory")
    pname = temp.name
    fp = stable_cache_subdir(pname, str(source_dir.resolve()))
    dest = paths.cache_dir / fp
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source_dir, dest)
    state = load_plugin_state(paths.state_file)
    state.installed[pname] = InstalledPluginRecord(
        marketplace="local",
        cache_subdir=fp,
        enabled=True,
    )
    save_plugin_state(paths.state_file, state)
    return pname, dest
