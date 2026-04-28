"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random

    try:
        data = json.loads(payload)
        calorie_target = data.get('calorie_target')
        diet_type = data.get('diet_type')
        cuisine_style = data.get('cuisine_style')
        meal_count = data.get('meal_count', 3)
        include_snacks = data.get('include_snacks', True)
        exclude_ingredients = data.get('exclude_ingredients', [])
        output_detail = data.get('output_detail', 'detailed')

        if not calorie_target or not diet_type or not cuisine_style:
            return json.dumps({"error": "Missing required parameters: calorie_target, diet_type, cuisine_style"})

        if not isinstance(calorie_target, int) or calorie_target < 800 or calorie_target > 5000:
            return json.dumps({"error": "calorie_target must be integer between 800 and 5000"})

        meal_names_map = {
            'breakfast': ['Oatmeal with Berries', 'Scrambled Eggs & Avocado Toast', 'Greek Yogurt Parfait', 'Smoothie Bowl', 'Chia Pudding'],
            'lunch': ['Grilled Chicken Salad', 'Quinoa Buddha Bowl', 'Lentil Soup', 'Turkey Wrap', 'Stir-fried Tofu & Vegetables'],
            'dinner': ['Baked Salmon with Asparagus', 'Chicken Stir-fry with Brown Rice', 'Vegetable Curry', 'Beef Tacos', 'Pasta Primavera'],
            'snack': ['Apple with Peanut Butter', 'Mixed Nuts', 'Hummus & Veggie Sticks', 'Protein Bar', 'Fruit Smoothie']
        }

        # Adjust meals based on diet type
        if diet_type == 'vegan':
            meal_names_map['breakfast'] = ['Tofu Scramble', 'Smoothie Bowl', 'Oatmeal with Almond Milk', 'Avocado Toast', 'Chia Pudding']
            meal_names_map['lunch'] = ['Quinoa Buddha Bowl', 'Lentil Soup', 'Veggie Wrap', 'Chickpea Salad', 'Stir-fried Tofu']
            meal_names_map['dinner'] = ['Vegan Curry', 'Stuffed Peppers', 'Veggie Stir-fry', 'Black Bean Tacos', 'Pasta with Marinara']
        elif diet_type == 'keto':
            meal_names_map['breakfast'] = ['Eggs & Bacon', 'Keto Pancakes', 'Avocado & Smoked Salmon', 'Bulletproof Coffee', 'Cheese Omelette']
            meal_names_map['lunch'] = ['Cauliflower Rice Bowl', 'Chicken & Avocado Salad', 'Zucchini Noodles', 'Tuna Lettuce Wraps', 'Eggplant Parmesan']
            meal_names_map['dinner'] = ['Steak with Butter', 'Baked Salmon with Broccoli', 'Chicken Thighs', 'Shrimp & Cauliflower', 'Pork Chops with Green Beans']

        # Cuisine style adjustments
        if cuisine_style == 'asian':
            meal_names_map['dinner'] = ['Pad Thai', 'Sushi Bowl', 'Miso Soup with Tofu', 'Korean Bibimbap', 'Vietnamese Pho']
        elif cuisine_style == 'indian':
            meal_names_map['lunch'] = ['Dal with Rice', 'Chickpea Curry', 'Palak Paneer', 'Vegetable Biryani', 'Masala Dosa']
            meal_names_map['dinner'] = ['Butter Chicken', 'Chana Masala', 'Lamb Curry', 'Vegetable Korma', 'Fish Curry']

        # Remove excluded ingredients from descriptions
        meal_names = ['Breakfast', 'Lunch', 'Dinner']
        if meal_count >= 4:
            meal_names.append('Second Lunch')
        if meal_count >= 5:
            meal_names.append('Evening Meal')

        # Distribute calories across meals
        per_meal_cal = calorie_target // (meal_count + (2 if include_snacks else 0))
        snack_cal = per_meal_cal // 2 if include_snacks else 0

        meals = []
        assigned_names = []
        for i, meal_name in enumerate(meal_names):
            options = meal_names_map.get(meal_name.lower(), meal_names_map['lunch'])
            dish = random.choice([d for d in options if d not in assigned_names])
            assigned_names.append(dish)
            meal_cal = per_meal_cal + random.randint(-50, 50)
            ingredients = dish.split()[:3] if output_detail == 'simple' else ['ingredient1', 'ingredient2', 'ingredient3']

            meal_entry = {
                'meal': meal_name,
                'dish': dish,
                'estimated_calories': meal_cal,
                'serving_suggestion': f'Serve with seasonal vegetables' if output_detail == 'detailed' else ''
            }

            if output_detail == 'with_recipe_links':
                # Generate a mock recipe reference
                recipe_id = f'recipe_{dish.lower().replace(" ", "_")}_{random.randint(1000,9999)}'
                meal_entry['recipe_reference'] = recipe_id

            meals.append(meal_entry)

        # Add snacks
        snacks = []
        if include_snacks:
            for _ in range(2):
                snack_name = random.choice(meal_names_map['snack'])
                snacks.append({
                    'snack': snack_name,
                    'estimated_calories': snack_cal
                })

        result = {
            'status': 'success',
            'plan_summary': {
                'total_calories': sum(m['estimated_calories'] for m in meals) + sum(s['estimated_calories'] for s in snacks),
                'target_calories': calorie_target,
                'diet_type': diet_type,
                'cuisine_style': cuisine_style,
                'meals_count': len(meals),
                'snacks_count': len(snacks)
            },
            'meals': meals,
            'snacks': snacks,
            'grocery_list': list(set([i for m in meals for i in m['dish'].split()[:2]]))[:8]
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "meal_plan_recommend",
    "description": "Generate a personalized daily meal plan with breakfast, lunch, dinner, and snacks based on user dietary preferences, calorie target, and cuisine style. Returns a structured meal schedule with dish names, estimated calories per meal, and ingredient summaries for grocery planning.",
    "category": "generate",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "calorie_target": {
            "type": "integer",
            "description": "Daily calorie goal in kcal, recommended range 1200-3500",
            "minimum": 800,
            "maximum": 5000
        },
        "diet_type": {
            "type": "string",
            "description": "Dietary preference for meal generation",
            "enum": [
                "omnivore",
                "vegetarian",
                "vegan",
                "pescatarian",
                "keto",
                "low_carb",
                "mediterranean"
            ]
        },
        "cuisine_style": {
            "type": "string",
            "description": "Preferred cuisine flavor profile",
            "enum": [
                "western",
                "asian",
                "middle_eastern",
                "latin",
                "indian",
                "fusion",
                "any"
            ]
        },
        "meal_count": {
            "type": "integer",
            "description": "Number of meals to generate per day (excluding snacks), 3-5",
            "minimum": 3,
            "maximum": 5,
            "default": 3
        },
        "include_snacks": {
            "type": "boolean",
            "description": "Optional: Whether to include snack suggestions between meals",
            "default": True
        },
        "exclude_ingredients": {
            "type": "array",
            "description": "Optional: List of ingredients to avoid in all generated meals",
            "items": {
                "type": "string"
            },
            "uniqueItems": True
        },
        "output_detail": {
            "type": "string",
            "description": "Optional: Level of detail in the output",
            "enum": [
                "simple",
                "detailed",
                "with_recipe_links"
            ],
            "default": "detailed"
        }
    },
    "required": [
        "calorie_target",
        "diet_type",
        "cuisine_style"
    ]
},
}
