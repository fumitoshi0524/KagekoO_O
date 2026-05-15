"""Kageko CLI package — Rich-powered terminal UI."""

from __future__ import annotations

from .app import app, _entrypoint
from .repl import ReplDispatcher
from .render import render_tool_table, render_tool_detail, render_skill_table, CATEGORY_COLORS, RISK_COLORS
from .setup import run_setup_wizard, load_global_config, save_global_config

__all__ = [
    "app",
    "_entrypoint",
    "ReplDispatcher",
    "render_tool_table",
    "render_tool_detail",
    "render_skill_table",
    "CATEGORY_COLORS",
    "RISK_COLORS",
    "run_setup_wizard",
    "load_global_config",
    "save_global_config",
]
