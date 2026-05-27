from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from kageko.tools.registry import ToolRegistry, Tool

logger = logging.getLogger("kageko.plugins")


@dataclass
class PluginManifest:
    name: str
    version: str = "0.0.0"
    description: str = ""
    tools: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)


class PluginContext:
    """Context object passed to plugins during registration."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.hooks: dict[str, list[Callable]] = {}

    def register_tool(self, tool: Tool) -> None:
        self.registry.register(tool)

    def register_hook(self, event: str, handler: Callable) -> None:
        self.hooks.setdefault(event, []).append(handler)


class PluginManager:
    """Discovers and loads plugins from configured directories."""

    def __init__(self, plugin_dirs: list[Path] | None = None):
        self.plugin_dirs = plugin_dirs or [
            Path.home() / ".kageko" / "plugins",
            Path.cwd() / ".kageko" / "plugins",
        ]
        self.plugins: list[PluginManifest] = []
        self.contexts: dict[str, PluginContext] = {}

    def discover(self) -> list[PluginManifest]:
        """Scan plugin directories for plugin.yaml manifests."""
        self.plugins.clear()
        for base_dir in self.plugin_dirs:
            if not base_dir.exists():
                continue
            for plugin_dir in base_dir.iterdir():
                manifest_path = plugin_dir / "plugin.yaml"
                if not manifest_path.is_file():
                    continue
                try:
                    data = yaml.safe_load(manifest_path.read_text())
                    manifest = PluginManifest(
                        name=data.get("name", plugin_dir.name),
                        version=data.get("version", "0.0.0"),
                        description=data.get("description", ""),
                        tools=data.get("tools", []),
                        hooks=data.get("hooks", []),
                    )
                    self.plugins.append(manifest)
                    logger.info("Discovered plugin: %s v%s", manifest.name, manifest.version)
                except Exception as e:
                    logger.warning("Failed to load plugin manifest %s: %s", manifest_path, e)
        return self.plugins

    def load(self, manifest: PluginManifest, registry: ToolRegistry, plugin_dir: Path) -> PluginContext:
        """Load a plugin by executing its __init__.py register(ctx) function."""
        ctx = PluginContext(registry=registry)
        init_path = plugin_dir / "__init__.py"
        if init_path.exists():
            spec = importlib.util.spec_from_file_location(
                f"kageko_plugin_{manifest.name}", init_path
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(ctx)
                    logger.info("Loaded plugin: %s", manifest.name)
        self.contexts[manifest.name] = ctx
        return ctx

    def load_all(self, registry: ToolRegistry) -> dict[str, PluginContext]:
        """Discover and load all plugins."""
        self.discover()
        for base_dir in self.plugin_dirs:
            if not base_dir.exists():
                continue
            for manifest in self.plugins:
                plugin_dir = base_dir / manifest.name
                if plugin_dir.exists():
                    try:
                        self.load(manifest, registry, plugin_dir)
                    except Exception as e:
                        logger.warning("Failed to load plugin %s: %s", manifest.name, e)
        return self.contexts
