"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    import random

    try:
        data = json.loads(payload)

        # Required fields
        required = ['age','weight_kg','height_cm','gender','activity_level','goal']
        for field in required:
            if field not in data:
                return f'error: missing required field "{field}"'

        age = data['age']
        weight = data['weight_kg']
        height = data['height_cm']
        gender = data['gender']
        activity = data['activity_level']
        goal = data['goal']
        restrictions = data.get('dietary_restrictions', [])
        if isinstance(restrictions, str):
            restrictions = [restrictions]
        # Normalize
        restrictions = [r.lower().replace(' ', '_') for r in restrictions]

        # Validate ranges
        if not (1 <= age <= 120):
            return 'error: age out of range (1-120)'
        if not (20.0 <= weight <= 300.0):
            return 'error: weight out of range (20-300 kg)'
        if not (50.0 <= height <= 250.0):
            return 'error: height out of range (50-250 cm)'

        # BMR (Mifflin-St Jeor)
        if gender == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        tdee = bmr * activity_multipliers.get(activity, 1.2)

        goal_adjustments = {
            'weight_loss': -500,
            'weight_maintenance': 0,
            'weight_gain': 500
        }
        adjustment = goal_adjustments.get(goal, 0)
        target_calories = tdee + adjustment

        # Override with custom calorie budget if provided
        if 'calorie_budget' in data:
            target_calories = data['calorie_budget']
        target_calories = max(800, min(5000, round(target_calories)))

        # Macronutrient split (simplified healthy distribution)
        # protein: 20%, carbs: 50%, fat: 30%
        protein_cal = target_calories * 0.20
        carb_cal = target_calories * 0.50
        fat_cal = target_calories * 0.30

        protein_g = round(protein_cal / 4)
        carb_g = round(carb_cal / 4)
        fat_g = round(fat_cal / 9)

        # Meal distribution: breakfast 25%, lunch 35%, dinner 30%, snack 10%
        meals = [
            {"name": "Breakfast", "calories_percent": 0.25, "time": "07:30-08:00"},
            {"name": "Lunch", "calories_percent": 0.35, "time": "12:00-13:00"},
            {"name": "Dinner", "calories_percent": 0.30, "time": "18:30-19:30"},
            {"name": "Snack", "calories_percent": 0.10, "time": "15:30-16:00"}
        ]

        # Sample food database (simplified, respecting restrictions)
        food_db = {
            "vegetarian": {
                "breakfast": ["Oatmeal with berries", "Greek yogurt with honey", "Scrambled tofu with spinach"],
                "lunch": ["Quinoa salad with chickpeas", "Lentil soup with whole grain bread", "Vegetable stir-fry with brown rice"],
                "dinner": ["Grilled portobello mushroom with sweet potato", "Vegetable curry with basmati rice", "Stuffed bell peppers with quinoa"],
                "snack": ["Apple with peanut butter", "Mixed nuts", "Protein smoothie with banana"]
            },
            "vegan": {
                "breakfast": ["Smoothie bowl with plant milk", "Oatmeal with almond milk and fruit", "Chia pudding with coconut milk"],
                "lunch": ["Buddha bowl with tahini dressing", "Black bean tacos with salsa", "Vegan sushi rolls"],
                "dinner": ["Vegan lentil bolognese with pasta", "Stuffed acorn squash with wild rice", "Vegan chili"],
                "snack": ["Hummus with carrot sticks", "Edamame", "Trail mix"]
            },
            "gluten_free": {
                "breakfast": ["Scrambled eggs with vegetables", "Rice cakes with avocado", "Yogurt parfait with gluten-free granola"],
                "lunch": ["Grilled chicken salad", "Black bean soup", "Zucchini noodles with pesto"],
                "dinner": ["Grilled salmon with quinoa", "Stuffed bell peppers with ground turkey", "Beef stir-fry with rice"],
                "snack": ["Cheese cubes", "Rice crackers with hummus", "Fresh fruit"]
            },
            "lactose_free": {
                "breakfast": ["Oatmeal with lactose-free milk", "Toast with jam", "Fruit salad"],
                "lunch": ["Grilled chicken wrap", "Lentil soup (no cream)", "Vegetable stir-fry"],
                "dinner": ["Baked cod with vegetables", "Grilled steak with sweet potato", "Chicken curry with rice"],
                "snack": ["Almonds", "Dark chocolate", "Rice cakes"]
            },
            "diabetic": {
                "breakfast": ["Egg white omelette with veggies", "Whole grain toast with avocado", "Berries with cottage cheese"],
                "lunch": ["Grilled chicken with mixed greens", "Tuna salad with olive oil dressing", "Turkey and vegetable wrap"],
                "dinner": ["Baked salmon with asparagus", "Stir-fried tofu with broccoli", "Lean beef with green beans"],
                "snack": ["Celery with almond butter", "Hard-boiled egg", "Handful of walnuts"]
            },
            "low_sodium": {
                "breakfast": ["Oatmeal with unsalted butter", "Fresh fruit bowl", "Poached eggs on toast"],
                "lunch": ["Grilled chicken breast with herbs", "Quinoa and vegetable salad", "Fresh vegetable wrap"],
                "dinner": ["Baked haddock with lemon", "Roasted turkey breast", "Vegetable soup (no salt)"],
                "snack": ["Unsalted almonds", "Fresh fruit", "Yogurt"]
            },
            "nut_free": {
                "breakfast": ["Scrambled eggs with cheese", "Porridge with seeds", "Yogurt with fruit"],
                "lunch": ["Grilled chicken sandwich", "Vegetable pasta", "Bean burrito"],
                "dinner": ["Baked chicken thighs", "Beef stew", "Vegetable curry with coconut milk"],
                "snack": ["Cheese sticks", "Veggie chips", "Pudding"]
            }
        }

        # Default menus for no restrictions
        default_foods = {
            "breakfast": ["Scrambled eggs with whole wheat toast", "Fruit smoothie with yogurt", "Oatmeal with nuts and banana"],
            "lunch": ["Grilled chicken salad with vinaigrette", "Turkey and cheese sandwich", "Vegetable soup with roll"],
            "dinner": ["Baked salmon with roasted vegetables", "Spaghetti with meat sauce", "Stir-fried chicken with broccoli and rice"],
            "snack": ["Apple slices with cheese", "Mixed nuts", "Yogurt with honey"]
        }

        # Select applicable food database: first matching restriction, or default
        food_source = None
        for r in restrictions:
            if r in food_db:
                food_source = food_db[r]
                break
        if food_source is None:
            food_source = default_foods

        # Build meal plan
        meal_plan = []
        for meal in meals:
            options = food_source.get(meal["name"].lower(), default_foods[meal["name"].lower()])
            # Use random for variety (simulated recommendation)
            chosen_food = random.choice(options)
            calories = round(target_calories * meal["calories_percent"])
            meal_plan.append({
                "meal": meal["name"],
                "time": meal["time"],
                "suggested_food": chosen_food,
                "calories": calories
            })

        result = {
            "patient": {
                "age": age,
                "weight_kg": weight,
                "height_cm": height,
                "gender": gender
            },
            "diet_plan": {
                "daily_calories": target_calories,
                "protein_g": protein_g,
                "carbohydrates_g": carb_g,
                "fat_g": fat_g,
                "meals": meal_plan
            },
            "goal": goal,
            "activity_level": activity,
            "dietary_restrictions_applied": restrictions if restrictions else ["none"]
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "patient_diet_plan_generator",
    "description": "Generate a personalized daily meal plan for a patient based on health profile, dietary restrictions, and nutritional goals, returning a structured diet schedule with calorie and macronutrient breakdown.",
    "category": "generate",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "age": {
            "type": "integer",
            "description": "Age of the patient in years, between 1 and 120.",
            "minimum": 1,
            "maximum": 120,
            "examples": [
                45
            ]
        },
        "weight_kg": {
            "type": "number",
            "description": "Body weight in kilograms, between 20.0 and 300.0.",
            "minimum": 20.0,
            "maximum": 300.0,
            "examples": [
                70.5
            ]
        },
        "height_cm": {
            "type": "number",
            "description": "Height in centimeters, between 50.0 and 250.0.",
            "minimum": 50.0,
            "maximum": 250.0,
            "examples": [
                175.0
            ]
        },
        "gender": {
            "type": "string",
            "description": "Biological sex for BMR calculation.",
            "enum": [
                "male",
                "female"
            ],
            "examples": [
                "male"
            ]
        },
        "activity_level": {
            "type": "string",
            "description": "Physical activity level multiplier.",
            "enum": [
                "sedentary",
                "light",
                "moderate",
                "active",
                "very_active"
            ],
            "examples": [
                "moderate"
            ]
        },
        "goal": {
            "type": "string",
            "description": "Nutritional goal of the diet plan.",
            "enum": [
                "weight_loss",
                "weight_maintenance",
                "weight_gain"
            ],
            "examples": [
                "weight_loss"
            ]
        },
        "dietary_restrictions": {
            "type": "array",
            "description": "Optional: List of dietary restrictions to exclude certain food types.",
            "items": {
                "type": "string",
                "enum": [
                    "vegetarian",
                    "vegan",
                    "gluten_free",
                    "lactose_free",
                    "diabetic",
                    "low_sodium",
                    "nut_free",
                    "none"
                ]
            },
            "examples": [
                [
                    "vegetarian",
                    "diabetic"
                ]
            ],
            "uniqueItems": true
        },
        "calorie_budget": {
            "type": "integer",
            "description": "Optional: Custom total daily calorie target in kcal. If not provided, it will be estimated from patient profile.",
            "minimum": 800,
            "maximum": 5000,
            "examples": [
                1800
            ]
        }
    },
    "required": [
        "age",
        "weight_kg",
        "height_cm",
        "gender",
        "activity_level",
        "goal"
    ]
},
}
