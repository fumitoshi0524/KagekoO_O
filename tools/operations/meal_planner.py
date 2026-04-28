"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)

        # Validate required fields
        if 'diet' not in data or 'calorie_target' not in data:
            return json.dumps({'error': 'Missing required fields: diet, calorie_target'})

        diet = data['diet']
        calorie_target = data['calorie_target']
        available = data.get('available_ingredients', [])
        meal_count = data.get('meal_count', 3)
        exclude = data.get('exclude_ingredients', [])
        cuisine = data.get('cuisine_preference', 'any')

        # Validate numeric types
        if not isinstance(calorie_target, int) or calorie_target < 500 or calorie_target > 5000:
            return json.dumps({'error': 'calorie_target must be integer between 500 and 5000'})
        valid_diets = ['vegetarian', 'vegan', 'paleo', 'keto', 'mediterranean', 'balanced', 'low_carb', 'gluten_free', 'dairy_free', 'nut_free', 'no_preference']
        if diet not in valid_diets:
            return json.dumps({'error': f'Invalid diet. Must be one of {valid_diets}'})

        # Recipe database (simplified for demonstration)
        recipes_pool = {
            'breakfast': [
                {'name': 'Oatmeal with Berries', 'ingredients': ['oats', 'berries', 'honey', 'almond_milk'], 'calories': 350, 'protein': 12, 'carbs': 60, 'fat': 8, 'cuisine': 'american', 'diet': ['vegetarian', 'vegan', 'gluten_free', 'dairy_free']},
                {'name': 'Scrambled Eggs', 'ingredients': ['eggs', 'butter', 'spinach'], 'calories': 300, 'protein': 20, 'carbs': 2, 'fat': 24, 'cuisine': 'american', 'diet': ['vegetarian', 'keto', 'gluten_free', 'dairy_free']},
                {'name': 'Greek Yogurt Parfait', 'ingredients': ['yogurt', 'granola', 'honey', 'berries'], 'calories': 400, 'protein': 15, 'carbs': 50, 'fat': 12, 'cuisine': 'greek', 'diet': ['vegetarian', 'gluten_free']},
                {'name': 'Smoothie Bowl', 'ingredients': ['banana', 'spinach', 'almond_milk', 'whey_protein', 'chia_seeds'], 'calories': 380, 'protein': 25, 'carbs': 45, 'fat': 10, 'cuisine': 'american', 'diet': ['vegetarian', 'gluten_free', 'dairy_free']},
                {'name': 'Avocado Toast', 'ingredients': ['bread', 'avocado', 'lemon', 'salt'], 'calories': 320, 'protein': 8, 'carbs': 30, 'fat': 20, 'cuisine': 'american', 'diet': ['vegetarian', 'vegan', 'dairy_free']}
            ],
            'lunch': [
                {'name': 'Chicken Salad', 'ingredients': ['chicken_breast', 'lettuce', 'tomato', 'cucumber', 'olive_oil', 'mustard'], 'calories': 450, 'protein': 40, 'carbs': 10, 'fat': 28, 'cuisine': 'american', 'diet': ['paleo', 'keto', 'gluten_free', 'dairy_free']},
                {'name': 'Veggie Wrap', 'ingredients': ['tortilla', 'hummus', 'bell_pepper', 'carrot', 'spinach'], 'calories': 400, 'protein': 15, 'carbs': 45, 'fat': 18, 'cuisine': 'mexican', 'diet': ['vegetarian', 'vegan', 'dairy_free']},
                {'name': 'Quinoa Bowl', 'ingredients': ['quinoa', 'black_beans', 'corn', 'avocado', 'cilantro', 'lime'], 'calories': 500, 'protein': 20, 'carbs': 65, 'fat': 18, 'cuisine': 'mexican', 'diet': ['vegetarian', 'vegan', 'gluten_free', 'dairy_free']},
                {'name': 'Minestrone Soup', 'ingredients': ['pasta', 'beans', 'tomato', 'carrot', 'celery', 'garlic'], 'calories': 350, 'protein': 15, 'carbs': 55, 'fat': 8, 'cuisine': 'italian', 'diet': ['vegetarian', 'vegan', 'dairy_free']},
                {'name': 'Tuna Salad', 'ingredients': ['tuna', 'mayonnaise', 'celery', 'onion', 'bell_pepper'], 'calories': 380, 'protein': 32, 'carbs': 5, 'fat': 26, 'cuisine': 'american', 'diet': ['keto', 'gluten_free', 'dairy_free']}
            ],
            'dinner': [
                {'name': 'Grilled Salmon', 'ingredients': ['salmon', 'asparagus', 'lemon', 'olive_oil', 'garlic'], 'calories': 550, 'protein': 45, 'carbs': 10, 'fat': 35, 'cuisine': 'american', 'diet': ['paleo', 'keto', 'gluten_free', 'dairy_free']},
                {'name': 'Chicken Tikka Masala', 'ingredients': ['chicken_breast', 'yogurt', 'tomato_sauce', 'garam_masala', 'rice'], 'calories': 600, 'protein': 40, 'carbs': 60, 'fat': 18, 'cuisine': 'indian', 'diet': ['gluten_free', 'dairy_free']},
                {'name': 'Vegetable Stir-fry', 'ingredients': ['tofu', 'broccoli', 'soy_sauce', 'ginger', 'garlic', 'rice'], 'calories': 420, 'protein': 25, 'carbs': 55, 'fat': 12, 'cuisine': 'asian', 'diet': ['vegetarian', 'vegan', 'dairy_free', 'gluten_free']},
                {'name': 'Beef Stew', 'ingredients': ['beef', 'carrot', 'potato', 'celery', 'beef_broth'], 'calories': 500, 'protein': 35, 'carbs': 40, 'fat': 18, 'cuisine': 'french', 'diet': ['paleo', 'gluten_free', 'dairy_free']},
                {'name': 'Pasta Carbonara', 'ingredients': ['pasta', 'eggs', 'parmesan', 'bacon', 'garlic'], 'calories': 650, 'protein': 30, 'carbs': 60, 'fat': 30, 'cuisine': 'italian', 'diet': ['gluten_free']}
            ],
            'snack': [
                {'name': 'Apple with Peanut Butter', 'ingredients': ['apple', 'peanut_butter'], 'calories': 200, 'protein': 8, 'carbs': 25, 'fat': 10, 'cuisine': 'american', 'diet': ['vegetarian', 'vegan', 'gluten_free', 'dairy_free']},
                {'name': 'Mixed Nuts', 'ingredients': ['almonds', 'walnuts', 'cashews'], 'calories': 180, 'protein': 6, 'carbs': 8, 'fat': 16, 'cuisine': 'american', 'diet': ['vegetarian', 'vegan', 'paleo', 'keto', 'gluten_free', 'dairy_free']},
                {'name': 'Protein Bar', 'ingredients': ['whey_protein', 'oats', 'honey', 'dark_chocolate'], 'calories': 250, 'protein': 15, 'carbs': 30, 'fat': 8, 'cuisine': 'american', 'diet': ['vegetarian', 'gluten_free']}
            ]
        }

        # Filter recipes based on diet and cuisine
        def filter_recipes(recipes, diet, cuisine, exclude):
            filtered = []
            for r in recipes:
                if diet != 'no_preference' and diet not in r['diet']:
                    continue
                if cuisine != 'any' and r['cuisine'] != cuisine:
                    continue
                if any(ing in exclude for ing in r['ingredients']):
                    continue
                if available:
                    if not any(ing in available for ing in r['ingredients']):
                        continue
                filtered.append(r)
            return filtered if filtered else recipes

        # Build weekly plan
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        week_plan = {}
        total_weekly_calories = 0

        for day in day_names:
            daily_meals = []
            remaining_calories = calorie_target
            # Distribute calories across meals (roughly 25% breakfast, 35% lunch, 35% dinner, 5% snack if applicable)
            distribution = []
            if meal_count >= 3:
                distribution = [0.25, 0.35, 0.30, 0.10][:meal_count]
            else:
                distribution = [0.45, 0.55][:meal_count] if meal_count == 2 else [1.0]
            # Adjust distribution to sum to 1
            total_dist = sum(distribution)
            distribution = [d/total_dist for d in distribution]

            meal_types = []
            if meal_count == 2:
                meal_types = ['lunch', 'dinner']
            elif meal_count == 3:
                meal_types = ['breakfast', 'lunch', 'dinner']
            elif meal_count == 4:
                meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
            elif meal_count == 5:
                meal_types = ['breakfast', 'lunch', 'snack', 'dinner', 'snack']

            for i, meal_type in enumerate(meal_types):
                target_cal = int(calorie_target * distribution[i])
                pool = recipes_pool.get(meal_type, recipes_pool['snack'])
                filtered = filter_recipes(pool, diet, cuisine, exclude)
                if not filtered:
                    # Fallback to unfiltered
                    filtered = pool
                # Pick closest recipe to target calories
                selected = min(filtered, key=lambda r: abs(r['calories'] - target_cal))
                daily_meals.append({
                    'type': meal_type,
                    'recipe': selected['name'],
                    'ingredients': selected['ingredients'],
                    'calories': selected['calories'],
                    'protein_g': selected['protein'],
                    'carbs_g': selected['carbs'],
                    'fat_g': selected['fat'],
                    'cuisine': selected['cuisine']
                })
                remaining_calories -= selected['calories']

            # Shuffle recipes each day for variety (but keep consistent across day)
            random.shuffle(daily_meals)
            day_calories = sum(m['calories'] for m in daily_meals)
            total_weekly_calories += day_calories

            week_plan[day] = {
                'meals': daily_meals,
                'total_daily_calories': day_calories,
                'remaining_calories': calorie_target - day_calories
            }

        # Generate shopping list (unique ingredients across the week)
        shopping_set = set()
        for day in week_plan.values():
            for meal in day['meals']:
                for ing in meal['ingredients']:
                    shopping_set.add(ing)
        shopping_list = sorted(list(shopping_set))

        # Nutritional summary
        avg_daily_calories = total_weekly_calories / 7
        avg_protein = sum(sum(m['protein_g'] for m in day['meals']) for day in week_plan.values()) / 7
        avg_carbs = sum(sum(m['carbs_g'] for m in day['meals']) for day in week_plan.values()) / 7
        avg_fat = sum(sum(m['fat_g'] for m in day['meals']) for day in week_plan.values()) / 7

        result = {
            'week_plan': week_plan,
            'weekly_summary': {
                'total_calories': round(total_weekly_calories, 1),
                'avg_daily_calories': round(avg_daily_calories, 1),
                'avg_daily_protein_g': round(avg_protein, 1),
                'avg_daily_carbs_g': round(avg_carbs, 1),
                'avg_daily_fat_g': round(avg_fat, 1),
                'target_daily_calorie': calorie_target
            },
            'shopping_list': {
                'ingredients': shopping_list,
                'count': len(shopping_list)
            },
            'diet_used': diet,
            'cuisine_preference': cuisine,
            'meals_per_day': meal_count,
            'generated_at': datetime.now().isoformat()
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "meal_planner",
    "description": "Generate a personalized weekly meal plan based on dietary preferences, calorie targets, and ingredient availability, returning a structured plan with recipes and nutritional summaries.",
    "category": "operations",
    "domain": "lifestyle",
    "risk_level": "none",
    "schema": {
    "type": "object",
    "properties": {
        "diet": {
            "type": "string",
            "description": "Dietary preference or restriction",
            "enum": [
                "vegetarian",
                "vegan",
                "paleo",
                "keto",
                "mediterranean",
                "balanced",
                "low_carb",
                "gluten_free",
                "dairy_free",
                "nut_free",
                "no_preference"
            ]
        },
        "calorie_target": {
            "type": "integer",
            "description": "Target daily calorie intake in kcal (e.g., 1800)",
            "minimum": 500,
            "maximum": 5000
        },
        "available_ingredients": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of ingredients you have on hand to minimize waste or shopping trips",
            "uniqueItems": True
        },
        "meal_count": {
            "type": "integer",
            "description": "Number of meals per day (2 for brunch/dinner, 3 for breakfast/lunch/dinner, 4 or 5 for small frequent meals)",
            "enum": [
                2,
                3,
                4,
                5
            ],
            "default": 3
        },
        "exclude_ingredients": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: Ingredients to avoid (e.g., 'mushrooms', 'cilantro')",
            "uniqueItems": True
        },
        "cuisine_preference": {
            "type": "string",
            "description": "Optional: Preferred cuisine style for variety",
            "enum": [
                "any",
                "italian",
                "mexican",
                "asian",
                "indian",
                "middle_eastern",
                "american",
                "french",
                "greek",
                "thai"
            ]
        }
    },
    "required": [
        "diet",
        "calorie_target"
    ]
},
}
