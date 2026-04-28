"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Save a personalized weekly meal plan by specifying dietary preferences, cuisine types, and number of meals per day, then retrieve the saved plan for household meal preparation."""
    import json
    try:
        data = json.loads(payload)
        action = data.get("action")
        if action not in ["save", "get"]:
            return json.dumps({"error": "Invalid action. Must be 'save' or 'get'."}, ensure_ascii=False)
        
        stored_plan = getattr(run, '_stored_plan', None)
        
        if action == "get":
            if stored_plan is None:
                return json.dumps({"error": "No meal plan is currently saved."}, ensure_ascii=False)
            return json.dumps({"status": "success", "meal_plan": stored_plan}, ensure_ascii=False)
        
        if action == "save":
            if "plan_summary" not in data or not data["plan_summary"]:
                return json.dumps({"error": "plan_summary is required for save action."}, ensure_ascii=False)
            try:
                plan = json.loads(data["plan_summary"])
            except json.JSONDecodeError:
                return json.dumps({"error": "plan_summary must be a valid JSON string."}, ensure_ascii=False)
            dietary = data.get("dietary_preference", "none")
            cuisine = data.get("cuisine_type", "any")
            meals_per_day = data.get("meals_per_day", 3)
            days = data.get("days", 7)
            if meals_per_day < 1 or meals_per_day > 5:
                return json.dumps({"error": "meals_per_day must be between 1 and 5."}, ensure_ascii=False)
            if days < 1 or days > 14:
                return json.dumps({"error": "days must be between 1 and 14."}, ensure_ascii=False)
            run._stored_plan = {
                "plan": plan,
                "dietary_preference": dietary,
                "cuisine_type": cuisine,
                "meals_per_day": meals_per_day,
                "days": days
            }
            return json.dumps({"status": "success", "message": "Meal plan saved successfully.", "meal_plan": run._stored_plan}, ensure_ascii=False)
        return json.dumps({"error": "Unexpected error."}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Failed to process request: {e}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "meal_plan_saver",
    "description": "Save a personalized weekly meal plan by specifying dietary preferences, cuisine types, and number of meals per day, then retrieve the saved plan for household meal preparation.",
    "category": "operations",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The operation to perform: 'save' to create or overwrite a meal plan, 'get' to retrieve the currently saved plan",
            "enum": [
                "save",
                "get"
            ]
        },
        "dietary_preference": {
            "type": "string",
            "description": "Optional: Dietary preference for the meal plan, such as 'vegetarian', 'vegan', 'gluten-free', 'keto', or 'none'",
            "enum": [
                "vegetarian",
                "vegan",
                "gluten-free",
                "keto",
                "none"
            ]
        },
        "cuisine_type": {
            "type": "string",
            "description": "Optional: Preferred cuisine type for the plan, e.g., 'italian', 'mexican', 'asian', 'american', or 'any'",
            "enum": [
                "italian",
                "mexican",
                "asian",
                "american",
                "any"
            ]
        },
        "meals_per_day": {
            "type": "integer",
            "description": "Optional: Number of meals to plan per day (default 3). Must be between 1 and 5.",
            "minimum": 1,
            "maximum": 5
        },
        "days": {
            "type": "integer",
            "description": "Optional: Number of days to generate the plan for (default 7). Must be between 1 and 14.",
            "minimum": 1,
            "maximum": 14
        },
        "plan_summary": {
            "type": "string",
            "description": "Required only for 'save' action: A JSON-formatted string representing the meal plan summary, e.g., a list of daily meals"
        }
    },
    "required": [
        "action"
    ]
},
}
