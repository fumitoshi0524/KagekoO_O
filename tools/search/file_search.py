"""Auto-generated tool module."""

from __future__ import annotations

import json
import re
from pathlib import Path


def run(payload: str) -> str:
    """Search for a pattern in file contents within a directory."""
    try:
        data = json.loads(payload)
        pattern = str(data.get("pattern", ""))
        directory = str(data.get("directory", "."))
        file_glob = str(data.get("glob", "*"))
        max_results = int(data.get("max_results", 20))
        case_sensitive = bool(data.get("case_sensitive", False))
    except (json.JSONDecodeError, TypeError, ValueError):
        return "error: invalid payload — provide JSON with 'pattern' and optional 'directory', 'glob', 'max_results', 'case_sensitive'"

    if not pattern:
        return "error: 'pattern' is required"

    search_dir = Path(directory).resolve()
    if not search_dir.exists():
        return f"error: directory not found: {directory}"
    if not search_dir.is_dir():
        return f"error: not a directory: {directory}"

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"error: invalid regex pattern — {e}"

    results: list[dict[str, object]] = []
    for filepath in search_dir.glob(file_glob):
        if not filepath.is_file():
            continue
        if filepath.name.startswith(".") or filepath.suffix in (".pyc", ".pyo", ".exe", ".dll", ".so"):
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_num, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                results.append({
                    "file": str(filepath.relative_to(search_dir)),
                    "line": line_num,
                    "content": line.strip()[:200],
                })
                if len(results) >= max_results:
                    break
        if len(results) >= max_results:
            break

    return json.dumps({
        "pattern": pattern,
        "directory": str(search_dir),
        "match_count": len(results),
        "results": results,
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "file_search",
    "description": "Search for a regex pattern across files in a directory. Returns matching file paths, line numbers, and line content.",
    "category": "search",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for in file contents."
            },
            "directory": {
                "type": "string",
                "description": "Directory path to search in (default: current directory)."
            },
            "glob": {
                "type": "string",
                "description": "File glob pattern to filter files (default: * for all files)."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 20)."
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the search is case-sensitive (default: False)."
            }
        },
        "required": ["pattern"]
    }
}
