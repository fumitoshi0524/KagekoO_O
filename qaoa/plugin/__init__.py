"""Kageko compatible plugin system.

This package provides a minimal compatibility layer for Claude Code's
plugin directory format (skills, hooks, agents, bundled MCP/LSP servers).
"""

from .manager import PluginManager  # noqa: F401

__all__ = ["PluginManager"]
