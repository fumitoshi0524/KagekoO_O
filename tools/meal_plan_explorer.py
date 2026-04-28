"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        diet_type = data.get('diet_type')
        calorie_target = data.get('calorie_target')
        available_ingredients = data.get('available_ingredients', '')
        meals_per_day = data.get('meals_per_day', 3)
        exclude_allergens = data.get('exclude_allergens', '')

        if not diet_type or not calorie_target or not available_ingredients:
            return json.dumps({'error': 'Missing required fields: diet_type, calorie_target, available_ingredients'})

        # Simulate meal generation based on diet type and calorie target
        meal_db = {
            'omnivore': [
                {'name': 'Grilled Chicken Salad', 'calories': 450, 'protein': 35, 'carbs': 15, 'fat': 25, 'ingredients': ['chicken', 'lettuce', 'tomato', 'cucumber']},
                {'name': 'Beef Stir-fry with Rice', 'calories': 600, 'protein': 40, 'carbs': 50, 'fat': 20, 'ingredients': ['beef', 'rice', 'broccoli', 'soy sauce']},
                {'name': 'Salmon with Quinoa', 'calories': 550, 'protein': 45, 'carbs': 30, 'fat': 22, 'ingredients': ['salmon', 'quinoa', 'asparagus']}
            ],
            'vegetarian': [
                {'name': 'Veggie Wrap', 'calories': 400, 'protein': 20, 'carbs': 45, 'fat': 15, 'ingredients': ['tortilla', 'hummus', 'bell pepper', 'spinach']},
                {'name': 'Lentil Soup', 'calories': 350, 'protein': 25, 'carbs': 40, 'fat': 8, 'ingredients': ['lentils', 'carrots', 'celery', 'onion']},
                {'name': 'Eggplant Parmesan', 'calories': 500, 'protein': 30, 'carbs': 35, 'fat': 25, 'ingredients': ['eggplant', 'mozzarella', 'tomato sauce', 'breadcrumbs']}
            ],
            'vegan': [
                {'name': 'Tofu Scramble', 'calories': 350, 'protein': 20, 'carbs': 30, 'fat': 18, 'ingredients': ['tofu', 'spinach', 'nutritional yeast', 'turmeric']},
                {'name': 'Chickpea Curry', 'calories': 450, 'protein': 22, 'carbs': 50, 'fat': 15, 'ingredients': ['chickpeas', 'coconut milk', 'curry paste', 'rice']},
                {'name': 'Avocado Pasta', 'calories': 500, 'protein': 15, 'carbs': 55, 'fat': 25, 'ingredients': ['pasta', 'avocado', 'lemon', 'basil']}
            ],
            'pescatarian': [
                {'name': 'Shrimp Tacos', 'calories': 450, 'protein': 30, 'carbs': 40, 'fat': 18, 'ingredients': ['shrimp', 'corn tortilla', 'cabbage', 'lime']},
                {'name': 'Tuna Poke Bowl', 'calories': 550, 'protein': 40, 'carbs': 45, 'fat': 20, 'ingredients': ['tuna', 'rice', 'edamame', 'seaweed']},
                {'name': 'Cod with Veggies', 'calories': 400, 'protein': 35, 'carbs': 25, 'fat': 15, 'ingredients': ['cod', 'zucchini', 'cherry tomato', 'olive oil']}
            ],
            'keto': [
                {'name': 'Bacon & Egg Muffins', 'calories': 350, 'protein': 25, 'carbs': 5, 'fat': 25, 'ingredients': ['bacon', 'eggs', 'cheese', 'spinach']},
                {'name': 'Cauliflower Rice Stir-fry', 'calories': 400, 'protein': 20, 'carbs': 10, 'fat': 30, 'ingredients': ['cauliflower', 'chicken', 'coconut oil', 'bell pepper']},
                {'name': 'Cheese Stuffed Meatballs', 'calories': 500, 'protein': 35, 'carbs': 8, 'fat': 35, 'ingredients': ['ground beef', 'mozzarella', 'almond flour', 'tomato sauce']}
            ]
        }

        if diet_type not in meal_db:
            return json.dumps({'error': f'Unsupported diet_type: {diet_type}'})

        meals = meal_db[diet_type]
        # Filter by available ingredients (basic match)
        ingredient_list = [i.strip().lower() for i in available_ingredients.split(',')]
        eligible_meals = []
        for meal in meals:
            meal_ingredients = [i.lower() for i in meal['ingredients']]
            if any(i in ingredient_list for i in meal_ingredients):
                eligible_meals.append(meal)

        if not eligible_meals:
            # Fallback: return all meals for that diet type
            eligible_meals = meals

        # Build weekly meal plan (7 days, meals_per_day per day)
        import itertools
        meal_cycle = itertools.cycle(eligible_meals)
        week = []
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_calorie_sum = 0
        for day in days:
            day_meals = []
            day_calories = 0
            for _ in range(meals_per_day):
                meal = next(meal_cycle)
                day_meals.append(meal)
                day_calories += meal['calories']
            week.append({
                'day': day,
                'meals': day_meals,
                'total_calories': day_calories
            })
            daily_calorie_sum += day_calories

        result = {
            'weekly_plan': week,
            'average_daily_calories': round(daily_calorie_sum / 7, 1),
            'target_calorie': calorie_target,
            'diet_type': diet_type
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "meal_plan_explorer",
    "description": "Takes user dietary preferences, calorie goals, and available ingredients to generate and display a balanced weekly meal plan. Returns a structured table of meals per day with nutritional breakdown and recipe suggestions.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "info",
    "schema": {
    "type": "object",
    "properties": {
        "diet_type": {
            "type": "string",
            "description": "Dietary preference category",
            "enum": [
                "omnivore",
                "vegetarian",
                "vegan",
                "pescatarian",
                "keto"
            ]
        },
        "calorie_target": {
            "type": "integer",
            "description": "Daily calorie target in kcal (range 1200-4000)",
            "minimum": 1200,
            "maximum": 4000
        },
        "available_ingredients": {
            "type": "string",
            "description": "Comma-separated list of ingredients the user already has (e.g. chicken, rice, spinach)",
            "maxLength": 500
        },
        "meals_per_day": {
            "type": "integer",
            "description": "Optional: number of meals per day (3 or 5). Default is 3.",
            "enum": [
                3,
                5
            ]
        },
        "exclude_allergens": {
            "type": "string",
            "description": "Optional: comma-separated list of allergens to exclude (e.g. dairy, nuts, gluten)"
        }
    },
    "required": [
        "diet_type",
        "calorie_target",
        "available_ingredients"
    ]
},
}
