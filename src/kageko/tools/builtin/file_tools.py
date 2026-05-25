# src/kageko/tools/builtin/file_tools.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


async def file_read(args: dict[str, Any]) -> str:
    path = Path(args["path"])
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"[ERROR] File not found: {path}"
    except PermissionError:
        return f"[ERROR] Permission denied: {path}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


async def file_write(args: dict[str, Any]) -> str:
    path = Path(args["path"])
    content = args["content"]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {path}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"


async def file_list(args: dict[str, Any]) -> str:
    path = Path(args["path"])
    try:
        entries = sorted(os.listdir(path))
        lines = []
        for entry in entries:
            full = path / entry
            marker = "/" if full.is_dir() else ""
            lines.append(f"{entry}{marker}")
        return "\n".join(lines) if lines else "(empty directory)"
    except FileNotFoundError:
        return f"[ERROR] Directory not found: {path}"
    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {e}"
