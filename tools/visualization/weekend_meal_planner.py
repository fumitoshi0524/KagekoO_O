"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        params = json.loads(payload)
        dietary = params.get('dietary_preference', 'none')
        calorie_target = params.get('calorie_target', None)
        cuisine = params.get('cuisine_style', 'any')
        include_tips = params.get('include_meal_prep_tips', False)

        # Real business logic: generate meal plan with predefined database
        meal_db = {
            'none': {
                'breakfast': ['Scrambled eggs', 'Pancakes', 'Fruit smoothie', 'Avocado toast'],
                'lunch': ['Grilled chicken salad', 'Turkey sandwich', 'Tomato soup', 'Quesadilla'],
                'dinner': ['Spaghetti bolognese', 'Beef stir-fry', 'Salmon with rice', 'Pizza']
            },
            'vegetarian': {
                'breakfast': ['Oatmeal with berries', 'Spinach omelette', 'Yogurt parfait', 'Banana pancakes'],
                'lunch': ['Caprese salad', 'Vegetable wrap', 'Lentil soup', 'Stuffed bell peppers'],
                'dinner': ['Eggplant parmesan', 'Vegetable curry', 'Mushroom risotto', 'Black bean tacos']
            },
            'vegan': {
                'breakfast': ['Smoothie bowl', 'Tofu scramble', 'Chia pudding', 'Fruit salad'],
                'lunch': ['Quinoa salad', 'Hummus wrap', 'Vegan chili', 'Sushi rolls (vegan)'],
                'dinner': ['Lentil stew', 'Stir-fried tofu', 'Vegan pasta', 'Stuffed zucchini']
            },
            'gluten_free': {
                'breakfast': ['Egg muffins', 'Rice porridge', 'Gluten-free pancakes', 'Fruit bowl'],
                'lunch': ['Grilled shrimp salad', 'Corn tortilla tacos', 'Zucchini noodles', 'Stuffed chicken'],
                'dinner': ['Grilled fish with veggies', 'Beef steak with sweet potato', 'Chicken stir-fry with rice', 'Stuffed peppers (GF)']
            },
            'keto': {
                'breakfast': ['Keto coffee', 'Bacon and eggs', 'Cheese omelette', 'Avocado egg cups'],
                'lunch': ['Caesar salad (no croutons)', 'Chicken avocado wrap (lettuce)', 'Tuna salad', 'Steak salad'],
                'dinner': ['Grilled salmon with asparagus', 'Zucchini lasagna', 'Keto meatballs', 'Stuffed mushrooms']
            }
        }
        cuisine_filter = {
            'italian': ['Pasta', 'Risotto', 'Pizza', 'Minestrone'],
            'mexican': ['Tacos', 'Burrito', 'Enchiladas', 'Guacamole'],
            'asian': ['Stir-fry', 'Sushi', 'Ramen', 'Curry'],
            'american': ['Burger', 'BBQ ribs', 'Mac and cheese', 'Apple pie'],
            'mediterranean': ['Hummus', 'Falafel', 'Gyros', 'Greek salad'],
            'any': []
        }

        days = ['Saturday', 'Sunday']
        meals_times = ['breakfast', 'lunch', 'dinner']
        plan = {}

        for day in days:
            day_plan = {}
            tip = ''
            # Choose meals avoiding repetition within a day
            used = []
            for meal_time in meals_times:
                options = meal_db.get(dietary, meal_db['none']).get(meal_time, [])
                if cuisine != 'any' and cuisine_filter.get(cuisine):
                    # Filter by cuisine if set
                    filtered = [m for m in options if any(cuisine_word.lower() in m.lower() for cuisine_word in cuisine_filter[cuisine])]
                    if filtered:
                        options = filtered
                # Pick first not used (simple cycle)
                chosen = None
                for opt in options:
                    if opt not in used:
                        chosen = opt
                        used.append(opt)
                        break
                if not chosen and options:
                    chosen = options[0]
                if not chosen:
                    chosen = 'Meal placeholder'
                day_plan[meal_time] = chosen
            if include_tips:
                tip = 'Prep tip: chop vegetables the night before to save time.'
            if calorie_target:
                day_plan['calorie_estimated'] = f'~{calorie_target-200}-{calorie_target+200} kcal'
            plan[day] = day_plan
            if include_tips:
                plan[f'{day}_tip'] = tip

        # Build a simple visual calendar string
        calendar_lines = ['Weekly Meal Plan']
        for day in days:
            calendar_lines.append(f'--- {day} ---')
            for mt in meals_times:
                if mt in plan[day]:
                    calendar_lines.append(f'  {mt.capitalize()}: {plan[day][mt]}')
            if include_tips:
                tip_key = f'{day}_tip'
                if tip_key in plan:
                    calendar_lines.append(f'  Tip: {plan[tip_key]}')
        calendar_str = '\n'.join(calendar_lines)

        result = {
            'meal_plan': plan,
            'calendar_view': calendar_str
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "weekend_meal_planner",
    "description": "Generate a visual weekly meal plan for the weekend, organizing breakfast, lunch, and dinner across Saturday and Sunday with optional dietary constraints, and return a human-readable list of meals per day, including a simple text-based calendar view.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "dietary_preference": {
            "type": "string",
            "enum": [
                "none",
                "vegetarian",
                "vegan",
                "gluten_free",
                "keto"
            ],
            "description": "Optional dietary preference to filter meal suggestions, default is 'none'."
        },
        "calorie_target": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 5000,
            "description": "Optional daily calorie target in kcal, if not provided no calorie filtering is applied."
        },
        "cuisine_style": {
            "type": "string",
            "enum": [
                "any",
                "italian",
                "mexican",
                "asian",
                "american",
                "mediterranean"
            ],
            "description": "Optional preferred cuisine style for the meals, default is 'any'."
        },
        "include_meal_prep_tips": {
            "type": "boolean",
            "description": "Optional: if True, include a short meal prep tip string at the end of each day's output."
        }
    },
    "required": []
},
}
