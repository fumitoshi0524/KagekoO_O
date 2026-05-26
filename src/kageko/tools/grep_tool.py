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


GREP_TOOL = {
    "name": "grep",
    "description": "Search file contents using ripgrep. Supports regex patterns.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {"type": "string", "description": "File or directory to search in"},
            "max_results": {"type": "integer", "description": "Maximum results (default 100)", "default": 100},
        },
        "required": ["pattern", "path"],
    },
    "category": "search",
}


async def grep_handler(args: dict) -> str:
    return grep(args["pattern"], args["path"], args.get("max_results", 100))
