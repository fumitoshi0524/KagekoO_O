# src/kageko/tools/builtin/file_tools.py
from __future__ import annotations

import os
from typing import Any

from kageko.tools.sandbox import resolve_path, SandboxViolation


async def file_read(args: dict[str, Any]) -> str:
    path_str = args.get("path")
    if not path_str:
        return "[ERROR] Missing required parameter: 'path'"
    try:
        path = resolve_path(path_str, must_exist=True)
        return path.read_text(encoding="utf-8")
    except SandboxViolation as e:
        return f"[SANDBOX] {e}"
    except FileNotFoundError:
        return f"[ERROR] File not found: {path_str}"
    except PermissionError:
        return f"[ERROR] Permission denied: {path_str}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


async def file_write(args: dict[str, Any]) -> str:
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
