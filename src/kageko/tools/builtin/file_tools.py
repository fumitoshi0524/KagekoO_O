"""File I/O tools — read, write, list with hashline anchor annotation."""

from __future__ import annotations

import os
from typing import Any

from kageko.tools.builtin.hashline_tool import annotate_file_read
from kageko.tools.sandbox import resolve_path, SandboxViolation


async def file_read(args: dict[str, Any]) -> str:
    """Read a file. Source files are auto-annotated with hashline anchors
    (``N#XXXXXXXX|line content``) so you can edit individual lines via the
    `hashline_edit` tool.  Copy the anchor, never invent one."""
    path_str = args.get("path")
    if not path_str:
        return "[ERROR] Missing required parameter: 'path'"
    try:
        path = resolve_path(path_str, must_exist=True)
        raw = path.read_text(encoding="utf-8")

        # Annotate with hashline anchors for source files
        ext = path.suffix.lower()
        source_exts = {
            ".py", ".rs", ".js", ".ts", ".tsx", ".jsx", ".go", ".java",
            ".c", ".cpp", ".h", ".hpp", ".toml", ".yaml", ".yml", ".json",
            ".md", ".txt", ".sh", ".bat", ".ps1", ".rb", ".php", ".swift",
            ".kt", ".scala", ".lua", ".r", ".sql", ".html", ".css", ".scss",
        }
        if ext in source_exts:
            annotated = annotate_file_read(raw, str(path))
            if annotated is not None:
                return annotated

        # Fallback: return raw (binary or too large)
        return raw
    except SandboxViolation as e:
        return f"[SANDBOX] {e}"
    except FileNotFoundError:
        return f"[ERROR] File not found: {path_str}"
    except PermissionError:
        return f"[ERROR] Permission denied: {path_str}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


async def file_write(args: dict[str, Any]) -> str:
    """Create a new file or overwrite an existing one entirely.

    Prefer `hashline_edit` for editing existing files — it targets a single
    line via anchor and is safer.  Use this tool ONLY for creating brand-new
    files that don't exist yet, or when you need to replace the ENTIRE file.
    """
    path_str = args.get("path")
    content = args.get("content")
    if not path_str:
        return "[ERROR] Missing required parameter: 'path'"
    if content is None:
        return "[ERROR] Missing required parameter: 'content'"
    try:
        path = resolve_path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {path}"
    except SandboxViolation as e:
        return f"[SANDBOX] {e}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


async def file_list(args: dict[str, Any]) -> str:
    path_str = args.get("path")
    if not path_str:
        return "[ERROR] Missing required parameter: 'path'"
    try:
        path = resolve_path(path_str, must_exist=True)
        entries = sorted(os.listdir(path))
        lines = []
        for entry in entries:
            full = path / entry
            marker = "/" if full.is_dir() else ""
            lines.append(f"{entry}{marker}")
        return "\n".join(lines) if lines else "(empty directory)"
    except SandboxViolation as e:
        return f"[SANDBOX] {e}"
    except FileNotFoundError:
        return f"[ERROR] Directory not found: {path_str}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"
