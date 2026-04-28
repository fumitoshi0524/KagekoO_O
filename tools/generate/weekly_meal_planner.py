"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    try:
        data = json.loads(payload)
        diet = data['diet_type']
        calories = data['daily_calorie_goal']
        excluded = data.get('excluded_ingredients', [])
        meals_per_day = data.get('meal_count_per_day', 4)
        
        # Meal database with calorie estimates per diet type
        meal_db = {
            "balanced": {
                "breakfast": [{"name": "Oatmeal with berries and nuts", "calories": 350}, {"name": "Scrambled eggs with whole wheat toast", "calories": 400}, {"name": "Greek yogurt parfait", "calories": 320}, {"name": "Smoothie bowl", "calories": 380}, {"name": "Avocado toast with egg", "calories": 420}],
                "lunch": [{"name": "Grilled chicken salad", "calories": 450}, {"name": "Turkey sandwich with veggies", "calories": 500}, {"name": "Quinoa bowl with roasted vegetables", "calories": 430}, {"name": "Tuna wrap", "calories": 480}, {"name": "Minestrone soup with bread", "calories": 400}],
                "dinner": [{"name": "Salmon with roasted asparagus", "calories": 550}, {"name": "Chicken stir-fry with brown rice", "calories": 600}, {"name": "Beef stew with vegetables", "calories": 580}, {"name": "Pasta with marinara and meatballs", "calories": 620}, {"name": "Baked cod with quinoa", "calories": 520}],
                "snack": [{"name": "Apple with peanut butter", "calories": 200}, {"name": "Mixed nuts", "calories": 180}, {"name": "Cheese stick", "calories": 150}, {"name": "Hummus with carrots", "calories": 170}, {"name": "Protein bar", "calories": 220}]
            },
            "vegetarian": {
                "breakfast": [{"name": "Veggie omelette", "calories": 340}, {"name": "Overnight oats", "calories": 360}, {"name": "Fruit and spinach smoothie", "calories": 310}, {"name": "Cottage cheese pancakes", "calories": 400}, {"name": "Yogurt with granola", "calories": 330}],
                "lunch": [{"name": "Caprese salad", "calories": 420}, {"name": "Vegetable curry with rice", "calories": 500}, {"name": "Grilled cheese with tomato soup", "calories": 460}, {"name": "Falafel wrap", "calories": 480}, {"name": "Spinach and feta pie", "calories": 440}],
                "dinner": [{"name": "Eggplant parmesan", "calories": 560}, {"name": "Mushroom risotto", "calories": 530}, {"name": "Vegetable lasagna", "calories": 580}, {"name": "Stuffed bell peppers", "calories": 500}, {"name": "Pumpkin curry", "calories": 510}],
                "snack": [{"name": "Trail mix", "calories": 190}, {"name": "Yogurt with honey", "calories": 160}, {"name": "Rice cakes with avocado", "calories": 180}, {"name": "Cottage cheese with pineapple", "calories": 150}, {"name": "Edamame", "calories": 140}]
            },
            "vegan": {
                "breakfast": [{"name": "Tofu scramble", "calories": 320}, {"name": "Chia pudding", "calories": 340}, {"name": "Banana oat pancakes", "calories": 370}, {"name": "Acai bowl", "calories": 390}, {"name": "Almond milk smoothie", "calories": 300}],
                "lunch": [{"name": "Vegan Buddha bowl", "calories": 450}, {"name": "Lentil soup", "calories": 400}, {"name": "Black bean tacos", "calories": 480}, {"name": "Hummus and vegetable wrap", "calories": 430}, {"name": "Quinoa tabbouleh", "calories": 410}],
                "dinner": [{"name": "Vegan pad thai", "calories": 540}, {"name": "Chickpea curry", "calories": 520}, {"name": "Stuffed portobello mushrooms", "calories": 480}, {"name": "Vegan chili", "calories": 500}, {"name": "Lentil bolognese with pasta", "calories": 560}],
                "snack": [{"name": "Mixed nuts and dried fruit", "calories": 200}, {"name": "Coconut yogurt", "calories": 140}, {"name": "Veggie sticks with hummus", "calories": 170}, {"name": "Smoothie with plant protein", "calories": 210}, {"name": "Dark chocolate", "calories": 180}]
            },
            "keto": {
                "breakfast": [{"name": "Bacon and eggs", "calories": 450}, {"name": "Keto avocado smoothie", "calories": 400}, {"name": "Cheese omelette", "calories": 420}, {"name": "Sausage with cauliflower hash", "calories": 480}, {"name": "Keto fat bombs", "calories": 350}],
                "lunch": [{"name": "Cauliflower rice bowl with chicken", "calories": 500}, {"name": "Cobb salad", "calories": 550}, {"name": "Zucchini noodles with pesto", "calories": 480}, {"name": "Tuna salad lettuce wraps", "calories": 450}, {"name": "Chicken avocado salad", "calories": 520}],
                "dinner": [{"name": "Steak with broccoli", "calories": 650}, {"name": "Salmon with asparagus", "calories": 600}, {"name": "Chicken thighs with cauliflower mash", "calories": 620}, {"name": "Pork chops with green beans", "calories": 580}, {"name": "Shrimp scampi with zucchini noodles", "calories": 550}],
                "snack": [{"name": "Celery with almond butter", "calories": 200}, {"name": "Cheese cubes", "calories": 180}, {"name": "Hard-boiled egg", "calories": 160}, {"name": "Pork rinds", "calories": 150}, {"name": "Macadamia nuts", "calories": 220}]
            },
            "mediterranean": {
                "breakfast": [{"name": "Greek yogurt with honey and walnuts", "calories": 340}, {"name": "Shakshuka", "calories": 380}, {"name": "Olive tapenade toast", "calories": 360}, {"name": "Feta and tomato omelette", "calories": 400}, {"name": "Baked egg in avocado", "calories": 370}],
                "lunch": [{"name": "Greek salad with grilled chicken", "calories": 450}, {"name": "Hummus and pita with veggies", "calories": 420}, {"name": "Falafel plate", "calories": 500}, {"name": "Tuna niçoise salad", "calories": 480}, {"name": "Stuffed grape leaves", "calories": 430}],
                "dinner": [{"name": "Grilled fish with lemon herbs", "calories": 520}, {"name": "Lamb souvlaki", "calories": 600}, {"name": "Chicken kabobs with tzatziki", "calories": 550}, {"name": "Baked eggplant with tomatoes and feta", "calories": 480}, {"name": "Seafood paella", "calories": 580}],
                "snack": [{"name": "Olives", "calories": 160}, {"name": "Feta cheese with tomatoes", "calories": 180}, {"name": "Baba ghanoush with cucumber", "calories": 150}, {"name": "Roasted chickpeas", "calories": 200}, {"name": "Dried figs", "calories": 170}]
            },
            "low_carb": {
                "breakfast": [{"name": "Egg and cheese muffin", "calories": 350}, {"name": "Chicken and avocado", "calories": 380}, {"name": "Crustless quiche", "calories": 360}, {"name": "Ham and cheese roll-ups", "calories": 340}, {"name": "Greek yogurt with seeds", "calories": 310}],
                "lunch": [{"name": "Roasted chicken and vegetables", "calories": 450}, {"name": "Tuna lettuce wraps", "calories": 400}, {"name": "Egg salad with greens", "calories": 430}, {"name": "Beef and broccoli bowl", "calories": 480}, {"name": "Shrimp and avocado salad", "calories": 420}],
                "dinner": [{"name": "Grilled salmon with green beans", "calories": 550}, {"name": "Chicken parmesan (no breading)", "calories": 520}, {"name": "Zucchini lasagna", "calories": 500}, {"name": "Turkey meatballs with marinara", "calories": 480}, {"name": "Stuffed chicken breast", "calories": 560}],
                "snack": [{"name": "Nuts", "calories": 200}, {"name": "Cheese stick", "calories": 150}, {"name": "Cucumber with cream cheese", "calories": 130}, {"name": "Pepperoni slices", "calories": 160}, {"name": "Celery with peanut butter", "calories": 180}]
            },
            "high_protein": {
                "breakfast": [{"name": "Protein pancakes", "calories": 380}, {"name": "Egg white omelette", "calories": 350}, {"name": "Protein smoothie bowl", "calories": 420}, {"name": "Cottage cheese and fruit", "calories": 340}, {"name": "Chicken breakfast sausage", "calories": 400}],
                "lunch": [{"name": "Grilled chicken breast with quinoa", "calories": 500}, {"name": "Tuna salad with chickpeas", "calories": 480}, {"name": "Turkey and cheese roll-ups", "calories": 450}, {"name": "Shrimp and quinoa bowl", "calories": 520}, {"name": "Beef and barley salad", "calories": 510}],
                "dinner": [{"name": "Sirloin steak with sweet potato", "calories": 650}, {"name": "Baked chicken thighs", "calories": 580}, {"name": "Grilled fish and beans", "calories": 550}, {"name": "Pork tenderloin with lentils", "calories": 600}, {"name": "Turkey chili", "calories": 520}],
                "snack": [{"name": "Protein shake", "calories": 220}, {"name": "Hard-boiled eggs (2)", "calories": 160}, {"name": "Beef jerky", "calories": 140}, {"name": "Greek yogurt", "calories": 180}, {"name": "Cottage cheese", "calories": 160}]
            }
        }
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        meal_types = ["breakfast", "lunch", "dinner", "snack"] if meals_per_day >= 4 else ["breakfast", "lunch", "dinner"] if meals_per_day == 3 else ["breakfast", "lunch"] if meals_per_day == 2 else ["breakfast", "lunch", "dinner", "snack"]
        
        plan = []
        for day in days:
            day_meals = []
            day_calories = 0
            available_meals = meal_db.get(diet, meal_db["balanced"])
            
            for meal_type in meal_types:
                options = available_meals.get(meal_type, [])
                # Filter out excluded ingredients
                filtered = [m for m in options if not any(excl.lower() in m["name"].lower() for excl in excluded)]
                if not filtered:
                    filtered = options  # fallback
                chosen = random.choice(filtered)
                day_meals.append({
                    "meal_type": meal_type,
                    "name": chosen["name"],
                    "calories": chosen["calories"]
                })
                day_calories += chosen["calories"]
            
            plan.append({
                "day": day,
                "meals": day_meals,
                "total_calories": day_calories
            })
        
        result = {
            "plan": plan,
            "diet_type": diet,
            "daily_calorie_target": calories,
            "average_calories_per_day": round(sum(d["total_calories"] for d in plan) / 7),
            "adherence_note": "Calorie estimates may vary based on portion sizes and preparation methods"
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "weekly_meal_planner",
    "description": "Generate a weekly meal plan based on dietary preferences, calorie goals, and ingredient restrictions. Returns a structured 7-day plan with breakfast, lunch, dinner, and snack suggestions for each day.",
    "category": "generate",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "diet_type": {
            "type": "string",
            "description": "Preferred diet style or restriction",
            "enum": [
                "balanced",
                "vegetarian",
                "vegan",
                "keto",
                "mediterranean",
                "low_carb",
                "high_protein"
            ]
        },
        "daily_calorie_goal": {
            "type": "integer",
            "description": "Target daily calorie intake in kcal",
            "minimum": 1200,
            "maximum": 4000
        },
        "excluded_ingredients": {
            "type": "array",
            "description": "Optional: List of ingredients to exclude from meals due to allergies or dislikes",
            "items": {
                "type": "string"
            }
        },
        "meal_count_per_day": {
            "type": "integer",
            "description": "Optional: Number of meals per day (including snacks). Default is 4",
            "minimum": 2,
            "maximum": 6
        }
    },
    "required": [
        "diet_type",
        "daily_calorie_goal"
    ]
},
}
