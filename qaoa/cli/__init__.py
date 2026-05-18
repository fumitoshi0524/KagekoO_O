"""Kageko CLI package — Rich-powered terminal UI."""

from __future__ import annotations

from .app import _entrypoint, app
from .config import load_global_config, save_global_config
from .errors import ErrorKind, classify_error, format_error
from .render import (
    CATEGORY_COLORS,
    RISK_COLORS,
    render_skill_table,
    render_tool_detail,
    render_tool_table,
)
from .repl import ReplDispatcher
from .setup import run_setup_wizard

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
    "classify_error",
    "format_error",
    "ErrorKind",
]
