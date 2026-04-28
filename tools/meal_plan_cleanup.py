"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, date
    try:
        data = json.loads(payload)
        plan_id = data.get('plan_id')
        if not plan_id:
            return json.dumps({'error': 'plan_id is required'})
        remove_past = data.get('remove_past_meals', True)
        remove_ingredients = data.get('remove_ingredients', [])
        keep_favorites = data.get('keep_favorites', False)
        
        # Simulated meal plan database lookup
        meal_plan = {
            'plan_id': plan_id,
            'name': 'Weekly Meal Plan',
            'meals': [
                {'id': 'm1', 'name': 'Pasta', 'date': '2023-10-01', 'ingredients': ['pasta', 'tomato sauce', 'cheese'], 'favorite': True},
                {'id': 'm2', 'name': 'Salad', 'date': '2023-10-02', 'ingredients': ['lettuce', 'tomato', 'dressing'], 'favorite': False},
                {'id': 'm3', 'name': 'Chicken', 'date': '2024-12-31', 'ingredients': ['chicken', 'rice', 'broccoli'], 'favorite': False},
            ]
        }
        
        today = date.today()
        removed_meals = []
        kept_meals = []
        
        for meal in meal_plan['meals']:
            meal_date = datetime.strptime(meal['date'], '%Y-%m-%d').date()
            should_remove = False
            
            if remove_past and meal_date < today:
                should_remove = True
            
            if should_remove and keep_favorites and meal.get('favorite'):
                should_remove = False
            
            if remove_ingredients and should_remove:
                for ing in remove_ingredients:
                    if ing.lower() in [i.lower() for i in meal['ingredients']]:
                        should_remove = True
                        break
            
            if should_remove:
                removed_meals.append(meal)
            else:
                kept_meals.append(meal)
        
        result = {
            'plan_id': plan_id,
            'status': 'cleaned',
            'total_meals_original': len(meal_plan['meals']),
            'meals_removed': len(removed_meals),
            'meals_kept': len(kept_meals),
            'removed_meal_names': [m['name'] for m in removed_meals],
            'kept_meal_names': [m['name'] for m in kept_meals],
            'cleaned_at': datetime.now().isoformat()
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "meal_plan_cleanup",
    "description": "Remove expired or unwanted entries from a user's saved meal plans and generate a summary of what was removed, enabling users to maintain an up-to-date weekly meal schedule.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "plan_id": {
            "type": "string",
            "description": "Unique identifier of the meal plan to clean up"
        },
        "remove_past_meals": {
            "type": "boolean",
            "description": "If true, remove all meals with dates before today",
            "default": true
        },
        "remove_ingredients": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of specific ingredient names to remove from all meals in the plan"
        },
        "keep_favorites": {
            "type": "boolean",
            "description": "Optional: If true, preserve meals marked as favorites even if they would otherwise be removed",
            "default": false
        }
    },
    "required": [
        "plan_id"
    ]
},
}
