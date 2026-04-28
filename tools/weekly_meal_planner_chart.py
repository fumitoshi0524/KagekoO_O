"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        meals = data.get('meals', [])
        if not meals:
            return json.dumps({'error': 'No meals provided'})
        # Build weekly grid structure
        days_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        meal_types = ['breakfast','lunch','dinner','snack']
        # Initialize empty grid
        grid = {day: {mt: None for mt in meal_types} for day in days_order}
        # Also track daily summaries
        daily_summary = {day: {'total_calories': 0, 'total_prep_minutes': 0, 'meal_count': 0} for day in days_order}
        for meal in meals:
            day = meal['day']
            mt = meal['meal_type']
            if day not in days_order:
                continue
            grid[day][mt] = {'name': meal['name'], 'prep': meal['estimated_prep_minutes']}
            daily_summary[day]['total_prep_minutes'] += meal['estimated_prep_minutes']
            daily_summary[day]['meal_count'] += 1
            if 'calories' in meal and meal['calories'] is not None:
                daily_summary[day]['total_calories'] += meal['calories']
        result = {'chart_data': grid, 'daily_summary': daily_summary}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})



TOOL_SPEC = {
    "name": "weekly_meal_planner_chart",
    "description": "Generate a visual weekly meal plan chart from a list of user-provided meals, including daily nutrition summaries and preparation time estimates, returned as a structured JSON object suitable for rendering a dashboard or printable grid.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "meals": {
            "type": "array",
            "description": "Array of meal objects for the week. Each meal must have a day (Monday-Sunday), meal_type (breakfast, lunch, dinner, snack), name, estimated_prep_minutes (integer 5-180), and optional calories (integer).",
            "items": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "enum": [
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday"
                        ],
                        "description": "Day of the week for this meal."
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": [
                            "breakfast",
                            "lunch",
                            "dinner",
                            "snack"
                        ],
                        "description": "Type of meal."
                    },
                    "name": {
                        "type": "string",
                        "description": "Name of the dish or meal."
                    },
                    "estimated_prep_minutes": {
                        "type": "integer",
                        "minimum": 5,
                        "maximum": 180,
                        "description": "Estimated preparation time in minutes."
                    },
                    "calories": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 2000,
                        "description": "Optional: Estimated calorie count for the meal."
                    }
                },
                "required": [
                    "day",
                    "meal_type",
                    "name",
                    "estimated_prep_minutes"
                ]
            },
            "minItems": 1,
            "maxItems": 28
        }
    },
    "required": [
        "meals"
    ]
},
}
