from __future__ import annotations

from kageko._native import ripgrep as _ripgrep


def grep(pattern: str, path: str, max_results: int = 100) -> str:
    """Search for pattern in files. Returns formatted results."""
    results = _ripgrep(pattern, path, max_results)
    if not results:
        return f"No matches for '{pattern}' in {path}"
    lines = []
    for m in results:
        lines.append(f"{m.path}:{m.line_number}: {m.line}")
    return "\n".join(lines)
