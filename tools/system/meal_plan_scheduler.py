"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        action = data.get("action")
        if not action:
            return json.dumps({"error": "Missing required field: action"})
        
        # Initialize storage (in production this would be persistent)
        if not hasattr(run, "meal_plan"):
            run.meal_plan = {}
        
        if action == "set":
            day = data.get("day")
            meal_type = data.get("meal_type")
            recipe_name = data.get("recipe_name")
            if not all([day, meal_type, recipe_name]):
                return json.dumps({"error": "Missing required fields: day, meal_type, recipe_name"})
            if day not in ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]:
                return json.dumps({"error": "Invalid day"})
            if meal_type not in ["breakfast","lunch","dinner","snack"]:
                return json.dumps({"error": "Invalid meal_type"})
            
            if day not in run.meal_plan:
                run.meal_plan[day] = {}
            run.meal_plan[day][meal_type] = recipe_name
            return json.dumps({"status": "added", "meal_plan": run.meal_plan})
        
        elif action == "get":
            return json.dumps({"meal_plan": run.meal_plan})
        
        elif action == "clear":
            run.meal_plan = {}
            return json.dumps({"status": "cleared", "meal_plan": {}})
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
            
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON input"})
    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "meal_plan_scheduler",
    "description": "Schedule and manage weekly meal plans by storing, retrieving, and clearing meal assignments for each day of the week. Operates on meal plan entries that include a day, meal type, and recipe name. Returns the current weekly meal plan for review, used to organize and track daily eating habits.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The operation to perform: 'set' to add a meal, 'get' to retrieve the current plan, 'clear' to reset all meals",
            "enum": [
                "set",
                "get",
                "clear"
            ]
        },
        "day": {
            "type": "string",
            "description": "Day of the week for the meal entry",
            "enum": [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday"
            ]
        },
        "meal_type": {
            "type": "string",
            "description": "Type of meal to schedule",
            "enum": [
                "breakfast",
                "lunch",
                "dinner",
                "snack"
            ]
        },
        "recipe_name": {
            "type": "string",
            "description": "Name of the recipe or dish for the scheduled meal"
        }
    },
    "required": [
        "action"
    ]
},
}
