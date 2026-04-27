"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Extract values from a JSON object using a dot-notation path."""
    try:
        data = json.loads(payload)
        json_obj = data.get("json", data.get("data", {}))
        path = str(data.get("path", ""))
    except (json.JSONDecodeError, TypeError):
        return "error: invalid payload — provide JSON with 'json' and 'path' fields"

    if isinstance(json_obj, str):
        try:
            json_obj = json.loads(json_obj)
        except json.JSONDecodeError:
            return "error: 'json' field is not valid JSON"

    if not path:
        return json.dumps(json_obj, indent=2, ensure_ascii=False)

    parts = path.split(".")
    current = json_obj
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return f"error: path '{path}' not found at key '{part}'"
            current = current[part]
        elif isinstance(current, list):
            try:
                idx = int(part)
                if idx < 0 or idx >= len(current):
                    return f"error: index {idx} out of range for path '{path}'"
                current = current[idx]
            except ValueError:
                return f"error: cannot index list with '{part}' in path '{path}'"
        else:
            return f"error: cannot traverse into {type(current).__name__} at '{part}' in path '{path}'"

    if isinstance(current, (dict, list)):
        return json.dumps(current, indent=2, ensure_ascii=False)
    return str(current)


TOOL_SPEC = {
    "name": "json_extract",
    "description": "Extract values from a JSON object using dot-notation path (e.g. 'users.0.name'). Returns the value at the given path.",
    "category": "analysis",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "json": {
                "type": "object",
                "description": "The JSON object or array to extract from."
            },
            "path": {
                "type": "string",
                "description": "Dot-notation path to the target value (e.g. 'data.users.0.email'). Leave empty to return the full object."
            }
        },
        "required": ["json"]
    }
}
