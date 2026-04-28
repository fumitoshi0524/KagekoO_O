"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a visual weekly meal plan summary from a list of meals."""
    import json
    try:
        data = json.loads(payload)
        meals = data.get("meals", [])
        if not meals:
            return json.dumps({"error": "At least one meal is required."}, ensure_ascii=False)
        
        # Validate required fields in each meal
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for meal in meals:
            if meal.get("day") not in valid_days:
                return json.dumps({"error": f"Invalid day '{meal.get('day')}'. Must be one of {valid_days}."}, ensure_ascii=False)
            if not meal.get("name") or not meal.get("ingredients"):
                return json.dumps({"error": "Each meal must have a name and at least one ingredient."}, ensure_ascii=False)
        
        # Organize by day
        day_order = {day: idx for idx, day in enumerate(valid_days)}
        meals.sort(key=lambda m: day_order.get(m["day"], 99))
        
        # Build weekly summary
        weekly_plan = {}
        total_calories = 0
        meal_count = 0
        for meal in meals:
            day = meal["day"]
            if day not in weekly_plan:
                weekly_plan[day] = []
            
            meal_entry = {
                "name": meal["name"],
                "ingredients": meal["ingredients"],
                "dietary_tags": meal.get("dietary_tags", [])
            }
            if "calories" in meal:
                meal_entry["calories"] = meal["calories"]
                total_calories += meal["calories"]
                meal_count += 1
            weekly_plan[day].append(meal_entry)
        
        result = {
            "weekly_meal_plan": weekly_plan,
            "summary": {
                "total_days_with_meals": len(weekly_plan),
                "total_meals": len(meals)
            }
        }
        
        # Add nutrition summary if requested
        include_nutrition = data.get("include_nutrition_summary", False)
        if include_nutrition and meal_count > 0:
            result["nutrition_summary"] = {
                "total_calories": total_calories,
                "average_calories_per_meal": round(total_calories / meal_count, 1)
            }
        
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload."}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "meal_planner_visualizer",
    "description": "Generate a visual weekly meal plan summary from a list of meals, including nutritional highlights, ingredient lists, and dietary tags for quick overview and meal prep.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "meals": {
            "type": "array",
            "description": "Array of meal objects for the week, each with name, day, main ingredients, and optional nutrition info.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the meal (e.g., 'Grilled Chicken Salad')."
                    },
                    "day": {
                        "type": "string",
                        "description": "Day of the week the meal is planned for (Monday through Sunday).",
                        "enum": [
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday"
                        ]
                    },
                    "ingredients": {
                        "type": "array",
                        "description": "List of main ingredients used in the meal.",
                        "items": {
                            "type": "string"
                        }
                    },
                    "calories": {
                        "type": "integer",
                        "description": "Optional: Total estimated calorie count for the meal (per serving)."
                    },
                    "dietary_tags": {
                        "type": "array",
                        "description": "Optional: Dietary tags such as 'vegetarian', 'gluten-free', 'high-protein', 'low-carb'.",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "name",
                    "day",
                    "ingredients"
                ]
            }
        },
        "include_nutrition_summary": {
            "type": "boolean",
            "description": "Optional: If True, include total weekly calorie count and average per day in the result."
        }
    },
    "required": [
        "meals"
    ]
},
}
