"""Auto-generated tool module."""

from __future__ import annotations

import json
import random


def run(payload: str) -> str:
    """Generate random numbers, pick from a list, or shuffle items."""
    try:
        data = json.loads(payload)
        mode = str(data.get("mode", "number")).lower().strip()
    except (json.JSONDecodeError, TypeError):
        return "error: invalid payload — provide JSON with 'mode'"

    if mode == "number":
        low = int(data.get("min", 0))
        high = int(data.get("max", 100))
        count = min(int(data.get("count", 1)), 100)
        if low > high:
            low, high = high, low
        results = [random.randint(low, high) for _ in range(count)]
        return json.dumps({"numbers": results}, indent=2)

    elif mode == "float":
        low = float(data.get("min", 0.0))
        high = float(data.get("max", 1.0))
        count = min(int(data.get("count", 1)), 100)
        decimals = int(data.get("decimals", 4))
        results = [round(random.uniform(low, high), decimals) for _ in range(count)]
        return json.dumps({"numbers": results}, indent=2)

    elif mode == "pick":
        items = data.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            return "error: 'items' must be a non-empty list"
        count = min(int(data.get("count", 1)), len(items))
        results = random.sample(items, count) if count <= len(items) else random.choices(items, k=count)
        return json.dumps({"picked": results}, indent=2, ensure_ascii=False)

    elif mode == "shuffle":
        items = list(data.get("items", []))
        if not isinstance(items, list) or len(items) == 0:
            return "error: 'items' must be a non-empty list"
        random.shuffle(items)
        return json.dumps({"shuffled": items}, indent=2, ensure_ascii=False)

    elif mode == "uuid":
        import uuid
        return json.dumps({"uuid": str(uuid.uuid4())}, indent=2)

    else:
        return f"error: unknown mode '{mode}'. Use: number, float, pick, shuffle, uuid"


TOOL_SPEC = {
    "name": "random_generate",
    "description": "Generate random integers, floats, UUIDs, pick random items from a list, or shuffle a list.",
    "category": "generate",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "description": "Generation mode: number (integer), float (decimal), pick (sample from list), shuffle (randomize list order), uuid (UUID v4).",
                "enum": ["number", "float", "pick", "shuffle", "uuid"]
            },
            "min": {
                "type": "number",
                "description": "Minimum value (for number/float mode, default: 0)."
            },
            "max": {
                "type": "number",
                "description": "Maximum value (for number/float mode, default: 100)."
            },
            "count": {
                "type": "integer",
                "description": "Number of items to generate/pick (default: 1, max: 100)."
            },
            "items": {
                "type": "array",
                "description": "List of items to pick from or shuffle (for pick/shuffle mode)."
            },
            "decimals": {
                "type": "integer",
                "description": "Number of decimal places for float mode (default: 4)."
            }
        },
        "required": ["mode"]
    }
}
