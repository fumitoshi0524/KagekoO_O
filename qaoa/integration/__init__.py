"""Integration layer — plugins, hooks, and MCP server."""

from __future__ import annotations

from .hooks import HooksEngine, HookHandler, HookEvent, HookContext, HookResult
from .plugin import PluginManager, PluginManifest, create_default_plugin_manager

__all__ = [
    "HooksEngine", "HookHandler", "HookEvent", "HookContext", "HookResult",
    "PluginManager", "PluginManifest", "create_default_plugin_manager",
]
