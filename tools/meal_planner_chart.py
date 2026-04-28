"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        required = ["household_size", "dietary_preference"]
        for r in required:
            if r not in data:
                return json.dumps({"error": f"Missing required parameter: {r}"})

        household_size = data["household_size"]
        if not isinstance(household_size, int) or household_size < 1 or household_size > 10:
            return json.dumps({"error": "household_size must be integer 1-10"})

        pref = data["dietary_preference"]
        valid_prefs = ["balanced", "vegetarian", "vegan", "keto", "mediterranean"]
        if pref not in valid_prefs:
            return json.dumps({"error": f"dietary_preference must be one of {valid_prefs}"})

        allergies_str = data.get("allergies", "")
        allergies = [a.strip().lower() for a in allergies_str.split(",") if a.strip()]

        meal_count = data.get("meal_count_per_day", 3)
        if meal_count not in [3, 4]:
            meal_count = 3

        start_date_str = data.get("start_date", "")
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            except:
                return json.dumps({"error": "start_date must be in YYYY-MM-DD format"})
        else:
            today = datetime.now()
            start_date = today - timedelta(days=today.weekday())

        # Generate simple meal plan based on preferences (simplified logic)
        meal_db = {
            "balanced": {
                "breakfast": ["Oatmeal with berries", "Scrambled eggs with toast", "Greek yogurt with granola"],
                "lunch": ["Chicken salad wrap", "Turkey sandwich", "Quinoa bowl"],
                "dinner": ["Grilled salmon with vegetables", "Chicken stir-fry", "Beef tacos"],
                "snack": ["Apple slices with peanut butter", "Mixed nuts", "Carrot sticks with hummus"]
            },
            "vegetarian": {
                "breakfast": ["Veggie omelette", "Smoothie bowl", "Avocado toast"],
                "lunch": ["Caprese salad", "Lentil soup", "Veggie wrap"],
                "dinner": ["Eggplant parmesan", "Mushroom risotto", "Vegetable curry"],
                "snack": ["Cheese sticks", "Fruit salad", "Yogurt cup"]
            },
            "vegan": {
                "breakfast": ["Smoothie bowl", "Tofu scramble", "Chia pudding"],
                "lunch": ["Vegan buddha bowl", "Black bean burger", "Sushi rolls"],
                "dinner": ["Vegan chili", "Stuffed bell peppers", "Pad thai"],
                "snack": ["Edamame", "Coconut chips", "Vegan protein bar"]
            },
            "keto": {
                "breakfast": ["Keto egg muffin", "Bacon and eggs", "Cream cheese pancakes"],
                "lunch": ["Cauliflower rice bowl", "Chicken Caesar salad (no croutons)", "Zucchini noodles with pesto"],
                "dinner": ["Grilled steak with asparagus", "Salmon with avocado salsa", "Butter chicken with cauliflower rice"],
                "snack": ["Cheese cubes", "Olives", "Celery with almond butter"]
            },
            "mediterranean": {
                "breakfast": ["Greek yogurt with honey and nuts", "Feta and tomato omelette", "Whole grain toast with hummus"],
                "lunch": ["Greek salad", "Hummus and pita plate", "Grilled vegetable sandwich"],
                "dinner": ["Lamb kebabs with tzatziki", "Baked fish with olives and tomatoes", "Stuffed grape leaves"],
                "snack": ["Olives", "Feta cheese", "Dried figs"]
            }
        }

        import random
        random.seed(hash((pref, household_size, start_date_str)))

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekly_plan = {}
        total_calories = 0

        for i, day in enumerate(days):
            day_date = start_date + timedelta(days=i)
            meals = {}
            day_calories = 0

            # Breakfast
            breakfast_options = meal_db[pref]["breakfast"]
            meals["breakfast"] = {
                "meal": random.choice(breakfast_options),
                "calories": random.randint(350, 500)
            }
            day_calories += meals["breakfast"]["calories"]

            # Lunch
            lunch_options = meal_db[pref]["lunch"]
            meals["lunch"] = {
                "meal": random.choice(lunch_options),
                "calories": random.randint(500, 700)
            }
            day_calories += meals["lunch"]["calories"]

            # Dinner
            dinner_options = meal_db[pref]["dinner"]
            meals["dinner"] = {
                "meal": random.choice(dinner_options),
                "calories": random.randint(600, 800)
            }
            day_calories += meals["dinner"]["calories"]

            if meal_count == 4:
                snack_options = meal_db[pref]["snack"]
                meals["snack"] = {
                    "meal": random.choice(snack_options),
                    "calories": random.randint(150, 250)
                }
                day_calories += meals["snack"]["calories"]

            weekly_plan[day] = {
                "date": day_date.strftime("%Y-%m-%d"),
                "meals": meals,
                "total_day_calories": day_calories
            }
            total_calories += day_calories

        # Generate grocery list (simplified extraction of common items)
        grocery_items = []
        for day in weekly_plan.values():
            for meal in day["meals"].values():
                if isinstance(meal, dict) and "meal" in meal:
                    meal_name = meal["meal"].lower()
                    words = meal_name.split()
                    for word in words:
                        word_clean = word.strip(".,!?").lower()
                        if word_clean in ["oatmeal","berries","eggs","toast","yogurt","granola","chicken","salad","wrap","turkey","sandwich","quinoa","salmon","vegetables","stir-fry","beef","tacos","apple","peanut","butter","nuts","carrot","hummus","spinach","tomato","cheese","bread","olive","lemon","garlic","onion","rice","pasta","sauce"] and word_clean not in grocery_items:
                            grocery_items.append(word_clean)

        result = {
            "weekly_meal_plan": weekly_plan,
            "average_daily_calories": round(total_calories / 7, 1),
            "grocery_list": sorted(grocery_items),
            "notes": f"Meal plan for {household_size} person(s) on {pref} diet. Avoids: {', '.join(allergies) if allergies else 'None'}"
        }

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "meal_planner_chart",
    "description": "Generate a weekly meal planner chart for a specified household, including daily breakfast, lunch, dinner, and snacks, with nutritional breakdown and grocery list, returned as a structured JSON array for dashboard display.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "household_size": {
            "type": "integer",
            "description": "Number of people in the household (1 to 10).",
            "minimum": 1,
            "maximum": 10
        },
        "dietary_preference": {
            "type": "string",
            "description": "Overall dietary preference for the week.",
            "enum": [
                "balanced",
                "vegetarian",
                "vegan",
                "keto",
                "mediterranean"
            ]
        },
        "allergies": {
            "type": "string",
            "description": "Optional: Comma-separated list of food allergies to avoid (e.g., 'peanuts,dairy,gluten'). If not provided, no allergies are considered."
        },
        "meal_count_per_day": {
            "type": "integer",
            "description": "Optional: Number of main meals per day (3 for 3 meals, 4 to include snacks). Defaults to 3 if not provided.",
            "default": 3,
            "enum": [
                3,
                4
            ]
        },
        "start_date": {
            "type": "string",
            "description": "Optional: Start date for the week in YYYY-MM-DD format. Defaults to the current Monday if not provided."
        }
    },
    "required": [
        "household_size",
        "dietary_preference"
    ]
},
}
