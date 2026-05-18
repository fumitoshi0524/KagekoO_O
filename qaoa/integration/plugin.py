"""Plugin system — discover, load, and manage Kageko plugins.

Each plugin is a directory with a plugin.json manifest:
{
    "name": "my-plugin",
    "version": "1.0.0",
    "description": "...",
    "skills": ["skills/"],           # relative paths to skill directories
    "hooks": [                        # optional hook definitions
        {"event": "PreToolUse", "type": "command", "command": "echo allow"}
    ],
    "mcpServers": {                   # optional MCP server definitions
        "my-server": {"command": "python", "args": ["-m", "my_mcp"]}
    },
    "lspServers": {}                  # optional LSP server definitions
}
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True, kw_only=True)
class PluginManifest:
    name: str
    version: str = "0.1.0"
    description: str = ""
    skills: list[str] = field(default_factory=list)
    hooks: list[dict[str, Any]] = field(default_factory=list)
    mcp_servers: dict[str, dict[str, Any]] = field(default_factory=dict)
    lsp_servers: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class LoadedPlugin:
    manifest: PluginManifest
    path: Path
    skills: list["SkillSpec"] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.manifest.name


@dataclass(slots=True, kw_only=True)
class PluginManager:
    """Discovers, loads, and manages plugins."""

    _plugins: dict[str, LoadedPlugin] = field(default_factory=dict)
    _plugin_dirs: list[Path] = field(default_factory=list)
    _skill_registry: object | None = None
    _conformance: object | None = None

    def add_search_dir(self, path: Path) -> None:
        if path not in self._plugin_dirs:
            self._plugin_dirs.append(path)

    def discover(self) -> list[PluginManifest]:
        """Discover all plugin.json manifests in search directories."""
        manifests: list[PluginManifest] = []
        seen: set[str] = set()
        for base in self._plugin_dirs:
            if not base.exists() or not base.is_dir():
                continue
            for item in sorted(base.iterdir()):
                if not item.is_dir():
                    continue
                manifest_path = item / "plugin.json"
                if manifest_path.exists() and manifest_path.is_file():
                    manifest = self._parse_manifest(manifest_path)
                    if manifest.name not in seen:
                        manifests.append(manifest)
                        seen.add(manifest.name)
        return manifests

    def load_plugin(self, base_path: Path) -> LoadedPlugin | None:
        """Load a single plugin from its base directory."""
        manifest_path = base_path / "plugin.json"
        if not manifest_path.exists():
            return None
        manifest = self._parse_manifest(manifest_path)
        return self._activate_plugin(manifest, base_path)

    def load_all(self) -> dict[str, LoadedPlugin]:
        """Discover and load all plugins."""
        manifests = self.discover()
        for manifest in manifests:
            if manifest.name in self._plugins:
                continue
            # Find the plugin directory
            for base in self._plugin_dirs:
                plugin_dir = base / manifest.name
                if plugin_dir.is_dir():
                    loaded = self._activate_plugin(manifest, plugin_dir)
                    if loaded:
                        self._plugins[manifest.name] = loaded
                    break
        return dict(self._plugins)

    def get_plugin(self, name: str) -> LoadedPlugin | None:
        return self._plugins.get(name)

    def get_all_skills(self) -> list["SkillSpec"]:
        """Get all skills from all loaded plugins."""
        from ..skills.loader import SkillLoader
        from ..skills.conformance import ConformanceEngine

        engine = ConformanceEngine()
        all_skills: list["SkillSpec"] = []

        for plugin in self._plugins.values():
            for skill_dir in plugin.manifest.skills:
                skill_path = plugin.path / skill_dir
                if not skill_path.is_dir():
                    continue
                loader = SkillLoader([skill_path])
                specs = loader.load_all()
                # All plugin skills go through conformance gate
                for spec in specs:
                    result = engine.validate(spec)
                    spec.metadata["conformance_passed"] = result.passed
                    spec.metadata["conformance_score"] = result.score
                    if not result.passed:
                        spec.metadata["conformance_issues"] = result.issues
                    spec.metadata["plugin"] = plugin.name
                    all_skills.append(spec)
        return all_skills

    def get_all_hooks(self) -> list[dict[str, Any]]:
        """Get all hook definitions from all loaded plugins."""
        hooks: list[dict[str, Any]] = []
        for plugin in self._plugins.values():
            hooks.extend(plugin.manifest.hooks)
        return hooks

    def get_all_mcp_servers(self) -> dict[str, dict[str, Any]]:
        """Get all MCP server definitions from all loaded plugins."""
        servers: dict[str, dict[str, Any]] = {}
        for plugin in self._plugins.values():
            for srv_name, srv_config in plugin.manifest.mcp_servers.items():
                namespaced = f"{plugin.name}:{srv_name}"
                servers[namespaced] = dict(srv_config)
        return servers

    def unload_plugin(self, name: str) -> None:
        self._plugins.pop(name, None)

    def _activate_plugin(self, manifest: PluginManifest, path: Path) -> LoadedPlugin:
        plugin = LoadedPlugin(manifest=manifest, path=path)
        plugin.skills = self.get_all_skills()
        return plugin

    @staticmethod
    def _parse_manifest(path: Path) -> PluginManifest:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return PluginManifest(
            name=str(data.get("name", path.parent.name)),
            version=str(data.get("version", "0.1.0")),
            description=str(data.get("description", "")),
            skills=_as_str_list(data.get("skills", [])),
            hooks=_as_dict_list(data.get("hooks", [])),
            mcp_servers=_as_dict_of_dicts(data.get("mcpServers", {})),
            lsp_servers=_as_dict_of_dicts(data.get("lspServers", {})),
        )


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _as_dict_list(value: object) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _as_dict_of_dicts(value: object) -> dict[str, dict[str, Any]]:
    if isinstance(value, dict):
        return {
            str(k): dict(v) if isinstance(v, dict) else {}
            for k, v in value.items()
        }
    return {}


def create_default_plugin_manager(
    *,
    project_plugins_dir: Path | None = None,
    user_plugins_dir: Path | None = None,
) -> PluginManager:
    """Create a plugin manager with standard search paths."""
    manager = PluginManager()

    # Project-level plugins
    if project_plugins_dir is None:
        project_plugins_dir = Path.cwd() / "plugins"
    manager.add_search_dir(project_plugins_dir)

    # User-level plugins
    if user_plugins_dir is None:
        user_plugins_dir = Path.home() / ".kageko" / "plugins"
    manager.add_search_dir(user_plugins_dir)

    return manager
