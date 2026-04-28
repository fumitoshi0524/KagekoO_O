"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze a meal's nutritional content from a list of food items and servings, returning macronutrient totals (calories, protein, fat, carbs) and a daily value percentage breakdown based on a 2000-calorie diet. Used for tracking dietary intake and meal planning."""
    import json
    try:
        data = json.loads(payload)
        items = data.get('items')
        if not items:
            return json.dumps({'error': 'No items provided'})
        # Internal food database: name -> (cal_per_100g, protein_per_100g, fat_per_100g, carbs_per_100g)
        food_db = {
            'banana': (89, 1.1, 0.3, 23.0),
            'apple': (52, 0.3, 0.2, 14.0),
            'chicken breast': (165, 31.0, 3.6, 0.0),
            'rice': (130, 2.7, 0.3, 28.0),
            'broccoli': (34, 2.8, 0.4, 7.0),
            'egg': (155, 13.0, 11.0, 1.1),
            'salmon': (208, 20.0, 13.0, 0.0),
            'avocado': (160, 2.0, 15.0, 9.0),
            'oatmeal': (71, 2.5, 1.5, 12.0),
            'milk': (42, 3.4, 1.0, 5.0),
            'beef steak': (271, 26.0, 19.0, 0.0),
            'sweet potato': (86, 1.6, 0.1, 20.0),
            'spinach': (23, 2.9, 0.4, 3.6),
            'almonds': (579, 21.0, 50.0, 22.0),
            'tuna': (144, 26.0, 4.9, 0.0)
        }
        total_calories = 0.0
        total_protein = 0.0
        total_fat = 0.0
        total_carbs = 0.0
        for item in items:
            name = item['name'].lower().strip()
            serving_g = item['serving_g']
            if name not in food_db:
                return json.dumps({'error': f'Unknown food: {item["name"]}'})
            cal, prot, fat, carbs = food_db[name]
            factor = serving_g / 100.0
            total_calories += cal * factor
            total_protein += prot * factor
            total_fat += fat * factor
            total_carbs += carbs * factor
        rdi_cal = 2000.0
        rdi_protein = 50.0
        rdi_fat = 65.0
        rdi_carbs = 300.0
        result = {
            'calories': round(total_calories, 1),
            'protein_g': round(total_protein, 1),
            'fat_g': round(total_fat, 1),
            'carbs_g': round(total_carbs, 1),
            'calories_dv_pct': round((total_calories / rdi_cal) * 100, 1),
            'protein_dv_pct': round((total_protein / rdi_protein) * 100, 1),
            'fat_dv_pct': round((total_fat / rdi_fat) * 100, 1),
            'carbs_dv_pct': round((total_carbs / rdi_carbs) * 100, 1)
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "meal_nutrition_analyzer",
    "description": "Analyze a meal's nutritional content from a list of food items and servings, returning macronutrient totals (calories, protein, fat, carbs) and a daily value percentage breakdown based on a 2000-calorie diet. Used for tracking dietary intake and meal planning.",
    "category": "analysis",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "description": "List of food items consumed in the meal",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Food name (e.g., 'banana', 'chicken breast')"
                    },
                    "serving_g": {
                        "type": "number",
                        "description": "Serving weight in grams"
                    }
                },
                "required": [
                    "name",
                    "serving_g"
                ]
            }
        },
        "activity_level": {
            "type": "string",
            "description": "Optional: Activity level for context (sedentary, moderate, active). If omitted, defaults to 'sedentary'.",
            "enum": [
                "sedentary",
                "moderate",
                "active"
            ]
        }
    },
    "required": [
        "items"
    ]
},
}
