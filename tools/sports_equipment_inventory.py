"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage and query sports equipment inventory."""
    import json
    try:
        data = json.loads(payload)
        action = data.get("action", "")
        item_name = data.get("item_name", "")
        quantity = data.get("quantity", 0)
        category = data.get("category", "")

        # In-memory inventory store (simulated persistence)
        if not hasattr(run, "inventory"):
            run.inventory = {
                "basketball": {"name": "basketball", "quantity": 10, "category": "balls"},
                "yoga mat": {"name": "yoga mat", "quantity": 5, "category": "fitness"},
                "tennis racket": {"name": "tennis racket", "quantity": 3, "category": "rackets"}
            }

        valid_actions = ["query", "add", "update_quantity", "remove"]
        if action not in valid_actions:
            return json.dumps({"error": f"Invalid action. Must be one of: {', '.join(valid_actions)}"})

        if action == "query":
            if category:
                filtered = {k: v for k, v in run.inventory.items() if v["category"] == category}
            else:
                filtered = dict(run.inventory)
            return json.dumps({"inventory": filtered}, ensure_ascii=False)

        if not item_name:
            return json.dumps({"error": "item_name is required for add, update_quantity, and remove actions."})

        item_key = item_name.lower()

        if action == "add":
            if item_key in run.inventory:
                run.inventory[item_key]["quantity"] += quantity
            else:
                run.inventory[item_key] = {"name": item_name, "quantity": quantity, "category": category or "general"}
            return json.dumps({"message": f"Added {quantity} of '{item_name}'.", "item": run.inventory[item_key]}, ensure_ascii=False)

        elif action == "update_quantity":
            if item_key not in run.inventory:
                return json.dumps({"error": f"Item '{item_name}' not found in inventory."})
            run.inventory[item_key]["quantity"] = quantity
            return json.dumps({"message": f"Updated quantity of '{item_name}' to {quantity}.", "item": run.inventory[item_key]}, ensure_ascii=False)

        elif action == "remove":
            if item_key not in run.inventory:
                return json.dumps({"error": f"Item '{item_name}' not found in inventory."})
            removed = run.inventory.pop(item_key)
            return json.dumps({"message": f"Removed '{item_name}' from inventory.", "removed_item": removed}, ensure_ascii=False)

        return json.dumps({"error": "Unexpected error."})

    except Exception as e:
        return f"error: {e}"


TOOL_SPEC = {
    "name": "sports_equipment_inventory",
    "description": "Manage and query the inventory of sports equipment items (e.g., balls, rackets, mats) by checking availability, adding new items, updating quantities, or removing items, and returns a current inventory report for facility management.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "query",
                "add",
                "update_quantity",
                "remove"
            ],
            "description": "Operation to perform on the equipment inventory."
        },
        "item_name": {
            "type": "string",
            "description": "Name of the equipment item (e.g., basketball, yoga mat). Required for all actions except query."
        },
        "quantity": {
            "type": "integer",
            "description": "Optional: Number to add or new total quantity for update_quantity. Must be non-negative.",
            "minimum": 0
        },
        "category": {
            "type": "string",
            "description": "Optional: Filter by equipment category (e.g., balls, fitness, protective) when action is query."
        }
    },
    "required": [
        "action"
    ]
},
}
