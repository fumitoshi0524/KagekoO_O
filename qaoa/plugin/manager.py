from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..config.settings import LSPConfig, MCPServer, Settings
from ..skills.registry import SkillRegistry
from .context import load_context_paths_content
from .hooks import HookEngine
from .loader import discover_plugins, load_plugin_from_dir
from .skills import build_skills_description, load_agent_files_for_plugin, load_skills_for_plugin
from .types import LoadedPlugin, PluginSkill

logger = logging.getLogger(__name__)


class PluginManager:
    """Central orchestrator for the Claude Code compatible plugin system.

    Responsibilities:
    - Discover and load plugins from user / project / extra directories.
    - Parse skills, hooks, MCP servers, LSP servers from each plugin.
    - Provide merged configs that can be injected into the rest of the app.
    - Expose a HookEngine for Agent lifecycle integration.
    """

    def __init__(self, settings: Settings, skill_registry: SkillRegistry | None = None) -> None:
        self._settings = settings
        self._plugins: list[LoadedPlugin] = []
        self._hook_engine: HookEngine | None = None
        self._context_content: str = ""
        self._skill_registry = skill_registry

    @property
    def plugins(self) -> list[LoadedPlugin]:
        return list(self._plugins)

    @property
    def hook_engine(self) -> HookEngine | None:
        return self._hook_engine

    @property
    def context_content(self) -> str:
        return self._context_content

    def discover_and_load(self) -> None:
        """Discover plugins, load skills/hooks, build HookEngine, load context_paths."""

        plugin_cfg = self._settings.plugins
        working_dir = self._settings.working_directory or "."

        if not plugin_cfg.enabled:
            logger.info("Plugin system disabled in configuration.")
            # Still load context_paths (CLAUDE.md, etc.) so the agent prompt is grounded.
            self._context_content = load_context_paths_content(
                working_dir=working_dir,
                context_paths=self._settings.context_paths,
            )
            return

        extra_dirs = [Path(d) for d in plugin_cfg.plugin_dirs] if plugin_cfg.plugin_dirs else None

        self._plugins = discover_plugins(
            working_dir=working_dir,
            extra_plugin_dirs=extra_dirs,
            settings=self._settings,
        )

        # Apply disabled_plugins from configuration.
        disabled = set(plugin_cfg.disabled_plugins)
        for p in self._plugins:
            if p.name in disabled:
                p.enabled = False

        # Load skills and agent stubs for each plugin.
        for plugin in self._plugins:
            if not plugin.enabled:
                continue
            plugin.skills = load_skills_for_plugin(plugin)
            if self._skill_registry is not None:
                for skill in plugin.skills:
                    self._skill_registry.install_skill(
                        name=skill.name,
                        tool_fn=lambda payload="": skill.content[:2000],
                        prompt=skill.content[:4000],
                        reference=f"plugin:{plugin.name}/{skill.name}",
                        category=skill.category or "operations",
                        domain=skill.domain or "technology",
                    )
            plugin.agents = load_agent_files_for_plugin(plugin)

        logger.info(
            "Loaded %d plugin(s): %s",
            len(self._plugins),
            ", ".join(p.name for p in self._plugins),
        )

        # Build HookEngine from loaded plugins.
        self._hook_engine = HookEngine(self._plugins)

        # Load context_paths content (CLAUDE.md, kageko.md, .cursorrules ...).
        self._context_content = load_context_paths_content(
            working_dir=working_dir,
            context_paths=self._settings.context_paths,
        )

    def get_all_skills(self) -> list[PluginSkill]:
        out: list[PluginSkill] = []
        for p in self._plugins:
            if p.enabled:
                out.extend(p.skills)
        return out

    def get_skills_description(self) -> str:
        return build_skills_description(self.get_all_skills())

    def get_merged_mcp_servers(self) -> dict[str, MCPServer]:
        """Merge MCP server configs from all enabled plugins.

        Plugin MCP servers are namespaced as ``plugin_name:server_name``
        to avoid collisions with user-configured servers.
        """
        merged: dict[str, MCPServer] = {}
        for p in self._plugins:
            if not p.enabled:
                continue
            for name, cfg in p.mcp_servers.items():
                key = f"{p.name}:{name}"
                merged[key] = cfg
        return merged

    def get_merged_lsp_servers(self) -> dict[str, LSPConfig]:
        merged: dict[str, LSPConfig] = {}
        for p in self._plugins:
            if not p.enabled:
                continue
            for name, cfg in p.lsp_servers.items():
                key = f"{p.name}:{name}"
                merged[key] = cfg
        return merged

    def enable_plugin(self, name: str) -> bool:
        from .ops import set_plugin_enabled
        from .paths import resolve_plugin_paths
        from .state import load_plugin_state

        found = False
        for p in self._plugins:
            if p.name == name:
                p.enabled = True
                found = True
                break
        if found:
            st = load_plugin_state(resolve_plugin_paths(self._settings).state_file)
            if name in st.installed:
                set_plugin_enabled(self._settings, name, True)
            self._hook_engine = HookEngine(self._plugins)
        return found

    def disable_plugin(self, name: str) -> bool:
        from .ops import set_plugin_enabled
        from .paths import resolve_plugin_paths
        from .state import load_plugin_state

        found = False
        for p in self._plugins:
            if p.name == name:
                p.enabled = False
                found = True
                break
        if found:
            st = load_plugin_state(resolve_plugin_paths(self._settings).state_file)
            if name in st.installed:
                set_plugin_enabled(self._settings, name, False)
            self._hook_engine = HookEngine(self._plugins)
        return found

    def install_plugin(self, source: str | Path) -> LoadedPlugin | None:
        """Install a plugin from a local directory into the cache and reload."""
        from .ops import FetchError, install_plugin_local_path

        source = Path(source)
        try:
            name, _dest = install_plugin_local_path(self._settings, source)
        except FetchError as e:
            logger.error("Plugin install failed: %s", e)
            return None
        self.discover_and_load()
        for p in self._plugins:
            if p.name == name:
                return p
        return None

    def uninstall_plugin(self, name: str) -> bool:
        from .ops import uninstall_plugin as ops_uninstall

        if not ops_uninstall(self._settings, name):
            return False
        self.discover_and_load()
        return True

    def list_plugins(self) -> list[dict[str, Any]]:
        """Return a summary list suitable for CLI display."""
        out: list[dict[str, Any]] = []
        for p in self._plugins:
            out.append({
                "name": p.name,
                "version": p.manifest.version or "0.0.0",
                "description": p.manifest.description or "",
                "enabled": p.enabled,
                "root": str(p.root),
                "skills": len(p.skills),
                "hooks": sum(len(v) for v in p.hooks.values()),
                "mcp_servers": len(p.mcp_servers),
            })
        return out
