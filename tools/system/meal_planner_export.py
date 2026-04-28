"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Export the user's weekly meal plan to a formatted text, grocery list, or CSV file."""
    import json
    try:
        data = json.loads(payload)
        plan_id = data.get('plan_id')
        fmt = data.get('format')
        include_recipes = data.get('include_recipes', False)
        dietary_tags = data.get('dietary_tags', [])

        if not plan_id or not fmt:
            return json.dumps({'error': 'Missing required parameters: plan_id, format'})

        # Simulated meal plan database
        meal_plans = {
            'week1': [
                {'day': 'Monday', 'meal': 'Breakfast', 'name': 'Oatmeal', 'tags': ['vegan', 'gluten_free'], 'recipe': {'ingredients': ['oats', 'water', 'banana'], 'steps': ['Boil water', 'Add oats', 'Cook 5 min', 'Top with banana']}},
                {'day': 'Monday', 'meal': 'Lunch', 'name': 'Salad', 'tags': ['vegetarian', 'gluten_free'], 'recipe': {'ingredients': ['lettuce', 'tomato', 'cucumber', 'dressing'], 'steps': ['Chop veggies', 'Mix', 'Add dressing']}},
                {'day': 'Monday', 'meal': 'Dinner', 'name': 'Pasta', 'tags': ['vegetarian'], 'recipe': {'ingredients': ['pasta', 'tomato sauce', 'cheese'], 'steps': ['Boil pasta', 'Heat sauce', 'Combine', 'Top with cheese']}}
            ]
        }

        plan = meal_plans.get(plan_id)
        if not plan:
            return json.dumps({'error': f'Meal plan not found: {plan_id}'})

        # Apply dietary filters
        if dietary_tags:
            filtered_plan = []
            for entry in plan:
                if all(tag in entry.get('tags', []) for tag in dietary_tags):
                    filtered_plan.append(entry)
            plan = filtered_plan

        # Generate export based on format
        if fmt == 'text':
            lines = []
            for entry in plan:
                line = f"{entry['day']} - {entry['meal']}: {entry['name']}"
                if include_recipes:
                    recipe = entry.get('recipe', {})
                    ing = ', '.join(recipe.get('ingredients', []))
                    steps = '; '.join(recipe.get('steps', []))
                    line += f"\n  Ingredients: {ing}\n  Steps: {steps}"
                lines.append(line)
            result = '\n'.join(lines)
            return json.dumps({'format': 'text', 'content': result, 'line_count': len(lines)})

        elif fmt == 'grocery_list':
            grocery_items = {}
            for entry in plan:
                if include_recipes:
                    for item in entry.get('recipe', {}).get('ingredients', []):
                        grocery_items[item] = grocery_items.get(item, 0) + 1
                else:
                    grocery_items[entry['name']] = grocery_items.get(entry['name'], 0) + 1
            items = [{'item': k, 'count': v} for k, v in sorted(grocery_items.items())]
            return json.dumps({'format': 'grocery_list', 'items': items, 'total_unique_items': len(items)})

        elif fmt == 'csv':
            header = 'Day,Meal,Name'
            if include_recipes:
                header += ',Ingredients,Steps'
            rows = []
            for entry in plan:
                row = f"{entry['day']},{entry['meal']},{entry['name']}"
                if include_recipes:
                    recipe = entry.get('recipe', {})
                    ing = '; '.join(recipe.get('ingredients', []))
                    steps = '; '.join(recipe.get('steps', []))
                    row += f",{ing},{steps}"
                rows.append(row)
            csv_content = header + '\n' + '\n'.join(rows)
            return json.dumps({'format': 'csv', 'content': csv_content, 'line_count': len(rows) + 1})

        else:
            return json.dumps({'error': f'Unsupported format: {fmt}'})

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "meal_planner_export",
    "description": "Export the user's weekly meal plan to a formatted text, grocery list, or CSV file. Operates on meal plan entries, recipes, and grocery items. Returns a structured export string ready for printing or saving.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "plan_id": {
            "type": "string",
            "description": "Unique identifier for the meal plan (e.g., week number or UUID)."
        },
        "format": {
            "type": "string",
            "description": "Desired export format.",
            "enum": [
                "text",
                "grocery_list",
                "csv"
            ]
        },
        "include_recipes": {
            "type": "boolean",
            "description": "Optional: Whether to include full recipe details (ingredients, steps) in the export. Defaults to False."
        },
        "dietary_tags": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "vegan",
                    "vegetarian",
                    "gluten_free",
                    "dairy_free",
                    "keto",
                    "paleo"
                ]
            },
            "description": "Optional: Filter plan items by dietary tags. Only meals matching all specified tags will be exported."
        }
    },
    "required": [
        "plan_id",
        "format"
    ]
},
}
