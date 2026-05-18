"""Kageko CLI command groups — each submodule registers a Typer app."""

from __future__ import annotations

from .chat import chat_command
from .config import config_app
from .pipeline import pipeline_app
from .session import session_app
from .skill import skill_app
from .tool import tool_app

__all__ = [
    "chat_command",
    "config_app",
    "pipeline_app",
    "session_app",
    "skill_app",
    "tool_app",
]
