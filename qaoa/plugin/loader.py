from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .types import (
    HookEvent,
    HookHandler,
    HookHandlerType,
    HookMatcherGroup,
    LoadedPlugin,
    PluginManifest,
)
from ..config.settings import LSPConfig, MCPServer, Settings
from ..storage_paths import iter_read_candidates

logger = logging.getLogger(__name__)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        logger.warning("Failed to read json: %s (%s)", path, e)
        return None


def _is_plugin_dir(plugin_dir: Path) -> bool:
    if not plugin_dir.is_dir():
        return False

    # Manifest (optional in Claude Code)
    if (plugin_dir / ".claude-plugin" / "plugin.json").exists():
        return True

    # Default locations
    markers = [
        plugin_dir / "skills",
        plugin_dir / "commands",
        plugin_dir / "agents",
        plugin_dir / "hooks" / "hooks.json",
        plugin_dir / ".mcp.json",
        plugin_dir / ".lsp.json",
    ]
    return any(p.exists() for p in markers)


def _parse_manifest(plugin_dir: Path) -> PluginManifest:
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    raw = _read_json(manifest_path) if manifest_path.exists() else None
    if not raw:
        return PluginManifest(name=plugin_dir.name)

    # Claude Code uses `name` as the only required field.
    raw_name = raw.get("name") or plugin_dir.name
    return PluginManifest.model_validate(raw | {"name": raw_name})


def _parse_hooks(plugin_dir: Path, manifest: PluginManifest) -> dict[HookEvent, list[HookMatcherGroup]]:
    raw: dict[str, Any] | None = None
    h = manifest.hooks
    if isinstance(h, dict):
        raw = h
    elif isinstance(h, str):
        hp = (plugin_dir / h).resolve()
        if hp.is_file():
            raw = _read_json(hp)

    if not raw:
        hooks_path = plugin_dir / "hooks" / "hooks.json"
        if hooks_path.exists():
            raw = _read_json(hooks_path)

    if not raw:
        manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
        raw_manifest = _read_json(manifest_path) if manifest_path.exists() else None
        hm = (raw_manifest or {}).get("hooks") if raw_manifest else None
        if isinstance(hm, dict):
            raw = hm

    if not raw:
        return {}

    # We expect either:
    # { "hooks": { "PostToolUse": [ ... ] } }
    # or direct mapping: { "PostToolUse": [ ... ] }
    maybe_hooks = raw.get("hooks", raw) if isinstance(raw, dict) else raw
    if not isinstance(maybe_hooks, dict):
        return {}

    out: dict[HookEvent, list[HookMatcherGroup]] = {}
    for event_name, groups in maybe_hooks.items():
        try:
            event = HookEvent(event_name)
        except Exception:
            # Unknown event: ignore for now (we can extend later).
            continue
        if not isinstance(groups, list):
            continue
        parsed_groups: list[HookMatcherGroup] = []
        for g in groups:
            if not isinstance(g, dict):
                continue
            matcher = g.get("matcher", "") or ""
            hooks_raw = g.get("hooks", [])
            if not isinstance(hooks_raw, list):
                hooks_raw = []
            handlers: list[HookHandler] = []
            for hr in hooks_raw:
                if not isinstance(hr, dict):
                    continue
                t = hr.get("type")
                if t == "command":
                    ht = HookHandlerType.COMMAND
                elif t == "prompt":
                    ht = HookHandlerType.PROMPT
                elif t == "agent":
                    ht = HookHandlerType.AGENT
                else:
                    continue
                handlers.append(
                    HookHandler(
                        type=ht,
                        command=hr.get("command"),
                        prompt=hr.get("prompt"),
                        agent=hr.get("agent"),
                        timeout=hr.get("timeout"),
                    )
                )
            parsed_groups.append(HookMatcherGroup(matcher=str(matcher), hooks=handlers))
        out[event] = parsed_groups
    return out


def _parse_mcp_servers(plugin_dir: Path, manifest: PluginManifest) -> dict[str, MCPServer]:
    raw: dict[str, Any] | None = None
    ms = manifest.mcpServers
    if isinstance(ms, str):
        mp = (plugin_dir / ms).resolve()
        if mp.is_file():
            raw = _read_json(mp)
    elif isinstance(ms, dict):
        raw = ms if "mcpServers" in ms else {"mcpServers": ms}

    if not raw:
        mcp_path = plugin_dir / ".mcp.json"
        raw = _read_json(mcp_path) if mcp_path.exists() else None
    if not raw:
        return {}

    # Claude Code uses:
    # { "mcpServers": { "name": { ... } } }
    servers_raw = raw.get("mcpServers")
    if not isinstance(servers_raw, dict):
        return {}

    out: dict[str, MCPServer] = {}
    for name, cfg in servers_raw.items():
        if not isinstance(cfg, dict):
            continue
        try:
            out[name] = MCPServer.model_validate(cfg | {"command": cfg.get("command", "")})
        except Exception as e:
            logger.warning("Invalid MCP server config for %s in %s: %s", name, plugin_dir, e)
    return out


def _parse_lsp_servers(plugin_dir: Path, manifest: PluginManifest) -> dict[str, LSPConfig]:
    raw: dict[str, Any] | None = None
    ls = manifest.lspServers
    if isinstance(ls, str):
        lp = (plugin_dir / ls).resolve()
        if lp.is_file():
            raw = _read_json(lp)
    elif isinstance(ls, dict):
        raw = ls

    if not raw:
        lsp_path = plugin_dir / ".lsp.json"
        raw = _read_json(lsp_path) if lsp_path.exists() else None
    if not raw:
        return {}

    if not isinstance(raw, dict):
        return {}

    out: dict[str, LSPConfig] = {}
    for name, cfg in raw.items():
        if not isinstance(cfg, dict):
            continue
        command = cfg.get("command")
        if not isinstance(command, str) or not command:
            continue
        args = cfg.get("args") if isinstance(cfg.get("args"), list) else []

        # Keep all other fields under `options`.
        options = {k: v for k, v in cfg.items() if k not in {"command", "args"}}
        try:
            out[name] = LSPConfig(command=command, args=list(args), options=options)
        except Exception as e:
            logger.warning("Invalid LSP server config for %s in %s: %s", name, plugin_dir, e)
    return out


def load_plugin_from_dir(plugin_dir: Path) -> LoadedPlugin | None:
    """Load a single plugin directory into memory."""
    if not _is_plugin_dir(plugin_dir):
        return None

    manifest = _parse_manifest(plugin_dir)
    return LoadedPlugin(
        name=manifest.name,
        root=plugin_dir,
        manifest=manifest,
        hooks=_parse_hooks(plugin_dir, manifest),
        mcp_servers=_parse_mcp_servers(plugin_dir, manifest),
        lsp_servers=_parse_lsp_servers(plugin_dir, manifest),
        enabled=True,
    )


def discover_plugins(
    *,
    working_dir: str | Path,
    extra_plugin_dirs: list[str | Path] | None = None,
    settings: Settings | None = None,
) -> list[LoadedPlugin]:
    # QAOA: skills must pass ConformanceEngine before use
    """Discover plugins from extra dirs, project, user plugins, and cache.

    Precedence (first plugin name wins): ``plugin_dirs`` entries, project
    ``.kageko/plugins`` -> ``.clawcode/plugins`` -> ``.claude/plugins``,
    user ``<data_root>/plugins/*`` (excluding ``cache``), then
    ``<data_root>/plugins/cache/*``.
    """
    from .paths import resolve_plugin_paths
    from .state import PluginState, load_plugin_state

    working_dir = Path(working_dir)
    ordered_entries: list[Path] = []

    if extra_plugin_dirs:
        for p in extra_plugin_dirs:
            root = Path(p)
            if root.is_dir():
                ordered_entries.extend(
                    sorted([x for x in root.iterdir() if x.is_dir()], key=lambda x: x.name)
                )

    for project_root in iter_read_candidates(working_dir, Path("plugins")):
        if project_root.is_dir():
            ordered_entries.extend(
                sorted([x for x in project_root.iterdir() if x.is_dir()], key=lambda x: x.name)
            )

    state: PluginState = PluginState()
    paths = None
    if settings is not None:
        paths = resolve_plugin_paths(settings)
        state = load_plugin_state(paths.state_file)
        up = paths.user_plugins_dir
        if up.is_dir():
            for x in sorted(up.iterdir(), key=lambda p: p.name):
                if x.is_dir() and x.name != "cache":
                    ordered_entries.append(x)
        if paths.cache_dir.is_dir():
            for x in sorted(paths.cache_dir.iterdir(), key=lambda p: p.name):
                if x.is_dir():
                    ordered_entries.append(x)
    else:
        # Legacy layout when no settings (tests): ~/.kageko, ~/.clawcode, ~/.claude
        for home_root in (Path.home() / ".kageko", Path.home() / ".clawcode", Path.home() / ".claude"):
            legacy = home_root / "plugins"
            if legacy.is_dir():
                for x in sorted(legacy.iterdir(), key=lambda p: p.name):
                    if x.is_dir() and x.name != "cache":
                        ordered_entries.append(x)

    # Package-bundled plugins (appended last: first occurrence of a plugin name still wins).
    builtin_root = Path(__file__).resolve().parent / "builtin_plugins"
    if builtin_root.is_dir():
        for x in sorted(builtin_root.iterdir(), key=lambda p: p.name):
            if x.is_dir():
                ordered_entries.append(x)

    subdir_enabled: dict[str, bool] = {}
    for _pname, rec in state.installed.items():
        subdir_enabled[rec.cache_subdir] = rec.enabled

    plugins: list[LoadedPlugin] = []
    seen: set[str] = set()

    for entry in ordered_entries:
        plugin = load_plugin_from_dir(entry)
        if not plugin:
            continue
        if plugin.name in seen:
            continue
        if paths and paths.cache_dir in entry.parents:
            sub = entry.name
            if sub in subdir_enabled:
                plugin.enabled = subdir_enabled[sub]
        seen.add(plugin.name)
        plugins.append(plugin)

    return plugins
