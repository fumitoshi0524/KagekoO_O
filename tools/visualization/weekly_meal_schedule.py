"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a weekly meal schedule visualization."""
    import json
    import random

    try:
        data = json.loads(payload)
        dietary = data.get('dietary_preference', 'any')
        cuisine = data.get('cuisine_style', 'any')
        meals_per_day = data.get('meals_per_day', 3)
        include_snacks = data.get('include_snacks', False)
        start_day = data.get('start_day', 'monday')

        if meals_per_day < 2 or meals_per_day > 5:
            return json.dumps({'error': 'meals_per_day must be between 2 and 5'})

        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        start_index = day_names.index(start_day)
        ordered_days = day_names[start_index:] + day_names[:start_index]

        meal_types = ['breakfast', 'lunch', 'dinner']
        if meals_per_day == 2:
            meal_types = ['lunch', 'dinner']
        elif meals_per_day == 4:
            meal_types = ['breakfast', 'lunch', 'snack', 'dinner']
        elif meals_per_day == 5:
            meal_types = ['breakfast', 'morning_snack', 'lunch', 'afternoon_snack', 'dinner']

        cuisine_bases = {
            'italian': ['pasta', 'pizza', 'risotto', 'bruschetta', 'lasagna'],
            'mexican': ['tacos', 'burritos', 'enchiladas', 'quesadillas', 'nachos'],
            'asian': ['stir_fry', 'sushi', 'ramen', 'dumplings', 'fried_rice'],
            'indian': ['curry', 'biryani', 'tandoori', 'dal', 'naan'],
            'american': ['burger', 'steak', 'sandwich', 'salad', 'bbq'],
            'mediterranean': ['hummus', 'falafel', 'gyros', 'tabbouleh', 'grilled_fish'],
            'fusion': ['taco_pizza', 'sushi_burrito', 'curry_pasta', 'ramen_burger', 'naan_pizza'],
            'any': ['mixed_grill', 'bowl', 'wrap', 'casserole', 'soup']
        }

        dietary_modifiers = {
            'vegetarian': '_vegetarian',
            'vegan': '_vegan',
            'gluten_free': '_gf',
            'keto': '_keto',
            'paleo': '_paleo',
            'mediterranean': '_med',
            'low_carb': '_lc',
            'any': ''
        }

        base_dishes = cuisine_bases.get(cuisine, cuisine_bases['any'])
        modifier = dietary_modifiers.get(dietary, '')

        week_plan = {}
        for day in ordered_days:
            day_meals = {}
            for meal in meal_types:
                dish = random.choice(base_dishes) + modifier
                day_meals[meal] = dish
            if include_snacks and meals_per_day < 5:
                snack_options = ['fruit', 'yogurt', 'nuts', 'granola_bar', 'smoothie']
                day_meals['snack'] = random.choice(snack_options)
            week_plan[day] = day_meals

        # Build ASCII visualization
        ascii_lines = []
        ascii_lines.append('+' + '-' * 77 + '+')
        ascii_lines.append(f"| {'WEEKLY MEAL SCHEDULE':^73} |")
        ascii_lines.append(f"| {'Diet: ' + dietary.replace('_', ' ').title() + ' | Cuisine: ' + cuisine.replace('_', ' ').title():^73} |")
        ascii_lines.append('+' + '-' * 77 + '+')

        meal_headers = [m.replace('_', ' ').title() for m in meal_types]
        header_str = ' | '.join([f"{h:^12}" for h in meal_headers])
        ascii_lines.append(f"| {'Day':^10} | {header_str} |")
        ascii_lines.append('+' + '-' * 77 + '+')

        for day in ordered_days:
            meals = week_plan[day]
            meal_strs = [f"{meals[m]:<12}" for m in meal_types]
            row = f"| {day.title():<10} | {' | '.join(meal_strs)} |"
            ascii_lines.append(row)

        ascii_lines.append('+' + '-' * 77 + '+')

        result = {
            'schedule': week_plan,
            'summary': {
                'dietary_preference': dietary.replace('_', ' ').title(),
                'cuisine_style': cuisine.replace('_', ' ').title(),
                'meals_per_day': meals_per_day,
                'snacks_included': include_snacks or meals_per_day > 3,
                'start_day': start_day.title()
            },
            'visualization': '\n'.join(ascii_lines)
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "weekly_meal_schedule",
    "description": "Generate a seven-day visual meal schedule based on user-specified dietary preferences, cuisine styles, and number of meals per day. Returns a structured daily plan with meal types, suggested dishes, and a simple ASCII-style weekly overview for easy printing or sharing.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "dietary_preference": {
            "type": "string",
            "description": "Dietary restriction or preference for meal planning",
            "enum": [
                "any",
                "vegetarian",
                "vegan",
                "gluten_free",
                "keto",
                "paleo",
                "mediterranean",
                "low_carb"
            ]
        },
        "cuisine_style": {
            "type": "string",
            "description": "Preferred cuisine style for the week",
            "enum": [
                "any",
                "italian",
                "mexican",
                "asian",
                "indian",
                "american",
                "mediterranean",
                "fusion"
            ]
        },
        "meals_per_day": {
            "type": "integer",
            "description": "Number of main meals to plan per day (2-5)",
            "minimum": 2,
            "maximum": 5
        },
        "include_snacks": {
            "type": "boolean",
            "description": "Optional: Whether to include snack suggestions between meals",
            "default": False
        },
        "start_day": {
            "type": "string",
            "description": "Optional: Starting day of the week (default: Monday)",
            "enum": [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday"
            ],
            "default": "monday"
        }
    },
    "required": [
        "dietary_preference",
        "cuisine_style",
        "meals_per_day"
    ]
},
}
