"""Diff utilities for session file changes.

Provides listing of file changes per session and optional unified diff
generation when old/new content is available.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from ..db.connection import get_database


async def get_changes_for_session(session_id: str) -> list[dict[str, Any]]:
    """Get file changes for a session from the database.

    Returns list of dicts with path, hash, created_at.
    """
    db = get_database()
    result: list[dict[str, Any]] = []
    raw = db.read_where("file_changes", key="session_id", value=session_id)
    raw.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    for fc in raw:
        result.append({
            "id": fc.get("id", ""),
            "path": fc.get("path", ""),
            "hash": fc.get("hash", ""),
            "created_at": fc.get("created_at", ""),
        })
    return result


def format_diff(old_content: str, new_content: str, path: str = "") -> str:
    """Produce unified diff between old and new content.

    Args:
        old_content: Previous file content
        new_content: Current file content
        path: Optional path label for diff header

    Returns:
        Unified diff string
    """
    a_lines = old_content.splitlines(keepends=True)
    b_lines = new_content.splitlines(keepends=True)
    if path:
        label = path.replace("\\", "/")
        diff = difflib.unified_diff(
            a_lines,
            b_lines,
            fromfile=label,
            tofile=label,
            lineterm="",
        )
    else:
        diff = difflib.unified_diff(a_lines, b_lines, lineterm="")
    return "".join(diff)


def get_current_file_content(file_path: str, max_size: int = 1024 * 1024) -> str:
    """Read current file content for display; return placeholder if missing or binary."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return f"(file not found: {file_path})"
    try:
        stat = path.stat()
        if stat.st_size > max_size:
            return f"(file too large: {stat.st_size} bytes)"
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        return f"(read error: {e})"
