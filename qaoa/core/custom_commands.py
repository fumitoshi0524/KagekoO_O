"""Custom command definitions loader.

Loads command definitions from:
- Project: .kageko/commands/*.json, .kageko/commands/*.yaml
- User: ~/.config/kageko/commands/*.json, ~/.config/kageko/commands/*.yaml
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

COMMANDS_DIR_NAME = "commands"
KAGEKO_DIR = ".kageko"
USER_CONFIG_DIR = ".config/kageko"


def _load_json(path: Path) -> list[dict[str, Any]]:
    """Load a single JSON file as list of command objects."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "commands" in data:
        return data["commands"]
    return []


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    """Load a single YAML file as list of command objects."""
    try:
        import yaml
    except ImportError:
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "commands" in data:
        return data["commands"]
    return []


def _normalize_command(raw: dict[str, Any]) -> dict[str, Any]:
    """Ensure command has id, name, description, command, args, placeholders."""
    return {
        "id": str(raw.get("id", raw.get("name", ""))),
        "name": str(raw.get("name", raw.get("id", "Unnamed"))),
        "description": str(raw.get("description", "")),
        "command": str(raw.get("command", "")),
        "args": list(raw.get("args", [])),
        "placeholders": dict(raw.get("placeholders", {})),
        "custom": True,
    }


def load_commands_from_directory(commands_dir: Path) -> list[dict[str, Any]]:
    """Load all command definitions from a directory.

    Reads *.json and *.yaml files; each file can be a list of commands
    or a dict with key "commands" containing the list.
    """
    out: list[dict[str, Any]] = []
    if not commands_dir.is_dir():
        return out
    for path in sorted(commands_dir.iterdir()):
        if path.suffix.lower() == ".json":
            for cmd in _load_json(path):
                out.append(_normalize_command(cmd))
        elif path.suffix.lower() in (".yaml", ".yml"):
            for cmd in _load_yaml(path):
                out.append(_normalize_command(cmd))
    return out


def get_custom_commands(working_dir: str | None = None) -> list[dict[str, Any]]:
    """Load custom commands from project and user config.

    Project commands (.kageko/commands/) are loaded first, then user
    (~/.config/kageko/commands/). Later entries override earlier by id.
    """
    by_id: dict[str, dict[str, Any]] = {}
    if working_dir:
        project_commands = Path(working_dir) / KAGEKO_DIR / COMMANDS_DIR_NAME
        for cmd in load_commands_from_directory(project_commands):
            by_id[cmd["id"]] = cmd
    user_commands_dir = Path.home() / USER_CONFIG_DIR / COMMANDS_DIR_NAME
    for cmd in load_commands_from_directory(user_commands_dir):
        by_id[cmd["id"]] = cmd
    return list(by_id.values())
