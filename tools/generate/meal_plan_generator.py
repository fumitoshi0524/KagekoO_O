"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random

    try:
        data = json.loads(payload)
        diet_type = data['diet_type']
        calorie_target = data['calorie_target']
        allergies = [a.lower().strip() for a in data.get('allergies', [])]
        cuisine_prefs = data.get('cuisine_preferences', [])
        meal_count = data.get('meal_count', 3)

        # Food database by meal type (simplified examples)
        food_db = {
            'breakfast': [
                ('Oatmeal with berries and almonds', 350, ['nuts']),
                ('Greek yogurt parfait with granola', 300, ['dairy']),
                ('Scrambled eggs with spinach', 250, ['eggs']),
                ('Smoothie bowl with banana and chia', 320, []),
                ('Whole grain toast with avocado', 280, ['gluten']),
            ],
            'lunch': [
                ('Grilled chicken salad with vinaigrette', 450, ['gluten']),
                ('Quinoa bowl with roasted vegetables', 400, []),
                ('Turkey and avocado wrap', 500, ['gluten', 'dairy']),
                ('Lentil soup with side salad', 380, []),
                ('Tuna salad on whole grain bread', 420, ['fish', 'gluten']),
            ],
            'dinner': [
                ('Salmon with asparagus and sweet potato', 550, ['fish']),
                ('Stir-fried tofu with vegetables and rice', 480, ['soy']),
                ('Beef stir-fry with broccoli', 520, []),
                ('Pasta primavera with tomato sauce', 500, ['gluten']),
                ('Stuffed bell peppers with ground turkey', 490, []),
            ],
            'snack': [
                ('Apple slices with peanut butter', 200, ['nuts']),
                ('Carrot sticks with hummus', 180, []),
                ('Mixed nuts and dried fruit', 220, ['nuts']),
                ('Rice cakes with cottage cheese', 190, ['dairy']),
                ('Protein shake', 250, ['dairy']),
            ]
        }

        # Filter out based on allergies
        def is_allowed(item, allergens):
            item_allergens = item[2]
            return not any(a in item_allergens for a in allergens)

        # Filter cuisine if preferences given (simplified: just adds variety)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        random.seed(42)  # for reproducibility
        plan = {}

        for day in days:
            daily_meals = []
            remaining_calories = calorie_target
            meal_types = ['breakfast', 'lunch', 'dinner']
            if meal_count >= 4:
                meal_types.append('snack')
            if meal_count == 5:
                meal_types.append('snack')
            random.shuffle(meal_types)
            # Distribute calories roughly
            for meal_type in meal_types:
                options = [item for item in food_db[meal_type] if is_allowed(item, allergies)]
                if not options:
                    continue
                # Pick item closest to remaining calories / meals left
                meal_options_sorted = sorted(options, key=lambda x: abs(x[1] - (remaining_calories // (len(meal_types) - len(daily_meals)))))
                chosen = random.choice(meal_options_sorted[:2])
                daily_meals.append({
                    'meal': meal_type.capitalize(),
                    'food': chosen[0],
                    'calories': chosen[1]
                })
                remaining_calories -= chosen[1]
                if remaining_calories < 200:
                    break
            plan[day] = daily_meals

        result = {
            'plan': plan,
            'summary': {
                'diet_type': diet_type,
                'calorie_target': calorie_target,
                'allergies_excluded': allergies,
                'total_days': 7
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "meal_plan_generator",
    "description": "Generate a personalized weekly meal plan based on dietary preferences, allergies, and calorie goals, returning a structured list of breakfast, lunch, dinner, and snack suggestions with estimated nutrition per day.",
    "category": "generate",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "diet_type": {
            "type": "string",
            "description": "Preferred dietary pattern",
            "enum": [
                "balanced",
                "vegetarian",
                "vegan",
                "keto",
                "low_carb",
                "mediterranean",
                "gluten_free",
                "paleo"
            ]
        },
        "allergies": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of food allergies or intolerances to exclude (e.g., nuts, dairy, soy, shellfish, eggs, gluten)"
        },
        "calorie_target": {
            "type": "integer",
            "description": "Target daily calorie intake in kcal (range 1200-4000)",
            "minimum": 1200,
            "maximum": 4000
        },
        "cuisine_preferences": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "american",
                    "italian",
                    "mexican",
                    "asian",
                    "indian",
                    "mediterranean",
                    "french",
                    "middle_eastern"
                ]
            },
            "description": "Optional: Preferred cuisine styles for variety"
        },
        "meal_count": {
            "type": "integer",
            "description": "Optional: Number of meals per day (default 3, max 5). Includes main meals + snacks if >3.",
            "minimum": 3,
            "maximum": 5,
            "default": 3
        }
    },
    "required": [
        "diet_type",
        "calorie_target"
    ]
},
}
