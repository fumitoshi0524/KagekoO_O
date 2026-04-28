"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for recipes by ingredient, cuisine type, dietary preference, or meal type. Returns matching recipe names, estimated prep time, difficulty level, and key ingredients."""
    import json
    import random
    import math

    try:
        data = json.loads(payload)
        ingredients = data.get('ingredients', '').strip()
        if not ingredients:
            return json.dumps({"error": "Missing required parameter: ingredients"}, ensure_ascii=False)

        cuisine = data.get('cuisine', '').strip().lower() if data.get('cuisine') else ''
        diet = data.get('diet', '').strip().lower() if data.get('diet') else ''
        meal_type = data.get('meal_type', '').strip().lower() if data.get('meal_type') else ''
        max_prep_time = data.get('max_prep_time', 480)
        max_results = min(data.get('max_results', 10), 50)
        sort_by = data.get('sort_by', 'relevance')

        # Parse ingredients list
        ingredient_list = [i.strip().lower() for i in ingredients.split(',') if i.strip()]
        if not ingredient_list:
            return json.dumps({"error": "Please provide at least one ingredient"}, ensure_ascii=False)

        # Extended recipe database with diverse options
        recipes = [
            {"name": "Classic Margherita Pizza", "cuisine": "italian", "diet": ["vegetarian"], "meal_type": ["dinner", "lunch"], "prep_time": 25, "difficulty": "easy", "ingredients": ["flour", "tomato", "mozzarella", "basil", "olive oil", "salt"]},
            {"name": "Chicken Tikka Masala", "cuisine": "indian", "diet": ["gluten-free"], "meal_type": ["dinner", "lunch"], "prep_time": 45, "difficulty": "medium", "ingredients": ["chicken", "yogurt", "tomato", "cream", "garlic", "ginger", "spices"]},
            {"name": "Vegetable Stir Fry", "cuisine": "chinese", "diet": ["vegan", "gluten-free", "low-carb"], "meal_type": ["dinner", "lunch"], "prep_time": 15, "difficulty": "easy", "ingredients": ["broccoli", "carrot", "bell pepper", "soy sauce", "garlic", "ginger", "oil"]},
            {"name": "Greek Salad", "cuisine": "greek", "diet": ["vegetarian", "gluten-free", "low-carb"], "meal_type": ["lunch", "dinner", "side"], "prep_time": 10, "difficulty": "easy", "ingredients": ["tomato", "cucumber", "olive", "feta", "onion", "olive oil", "oregano"]},
            {"name": "Beef Tacos", "cuisine": "mexican", "diet": ["gluten-free"], "meal_type": ["dinner", "lunch"], "prep_time": 20, "difficulty": "easy", "ingredients": ["beef", "tortilla", "lettuce", "tomato", "cheese", "sour cream", "salsa"]},
            {"name": "Miso Soup", "cuisine": "japanese", "diet": ["vegan", "dairy-free", "low-fat"], "meal_type": ["dinner", "lunch", "appetizer"], "prep_time": 10, "difficulty": "easy", "ingredients": ["miso paste", "tofu", "seaweed", "green onion", "dashi"]},
            {"name": "Chocolate Chip Cookies", "cuisine": "american", "diet": ["vegetarian"], "meal_type": ["dessert", "snack"], "prep_time": 30, "difficulty": "easy", "ingredients": ["flour", "butter", "sugar", "chocolate", "egg", "vanilla"]},
            {"name": "Pad Thai", "cuisine": "thai", "diet": ["gluten-free", "dairy-free"], "meal_type": ["dinner", "lunch"], "prep_time": 25, "difficulty": "medium", "ingredients": ["rice noodles", "shrimp", "tofu", "peanut", "bean sprout", "lime", "fish sauce"]},
            {"name": "French Onion Soup", "cuisine": "french", "diet": ["vegetarian"], "meal_type": ["dinner", "appetizer"], "prep_time": 60, "difficulty": "medium", "ingredients": ["onion", "butter", "beef broth", "bread", "cheese", "thyme"]},
            {"name": "Bibimbap", "cuisine": "korean", "diet": ["gluten-free"], "meal_type": ["dinner", "lunch"], "prep_time": 35, "difficulty": "medium", "ingredients": ["rice", "beef", "egg", "spinach", "carrot", "mushroom", "gochujang"]},
            {"name": "Pho Bo", "cuisine": "vietnamese", "diet": ["gluten-free", "dairy-free"], "meal_type": ["dinner", "lunch"], "prep_time": 120, "difficulty": "hard", "ingredients": ["beef", "rice noodles", "beef broth", "star anise", "cilantro", "lime", "bean sprout"]},
            {"name": "Keto Avocado Egg Cups", "cuisine": "american", "diet": ["keto", "low-carb", "gluten-free"], "meal_type": ["breakfast", "snack"], "prep_time": 20, "difficulty": "easy", "ingredients": ["avocado", "egg", "cheese", "salt", "pepper"]},
            {"name": "Vegan Buddha Bowl", "cuisine": "mediterranean", "diet": ["vegan", "gluten-free", "high-protein"], "meal_type": ["dinner", "lunch"], "prep_time": 25, "difficulty": "easy", "ingredients": ["quinoa", "chickpea", "sweet potato", "kale", "tahini", "lemon"]},
            {"name": "Paleo Chicken Salad", "cuisine": "american", "diet": ["paleo", "gluten-free", "dairy-free"], "meal_type": ["lunch", "dinner"], "prep_time": 15, "difficulty": "easy", "ingredients": ["chicken", "celery", "apple", "walnut", "olive oil", "mustard"]},
            {"name": "Low-Carb Zucchini Noodles", "cuisine": "italian", "diet": ["low-carb", "keto", "vegetarian", "gluten-free"], "meal_type": ["dinner", "lunch"], "prep_time": 15, "difficulty": "easy", "ingredients": ["zucchini", "tomato", "garlic", "olive oil", "basil", "parmesan"]},
            {"name": "Overnight Oats", "cuisine": "american", "diet": ["vegetarian", "high-protein"], "meal_type": ["breakfast"], "prep_time": 5, "difficulty": "easy", "ingredients": ["oats", "milk", "yogurt", "honey", "berry", "chia seed"]},
            {"name": "Gluten-Free Banana Pancakes", "cuisine": "american", "diet": ["gluten-free", "vegetarian"], "meal_type": ["breakfast"], "prep_time": 15, "difficulty": "easy", "ingredients": ["banana", "egg", "gluten-free flour", "baking powder", "cinnamon"]},
            {"name": "Dairy-Free Creamy Mushroom Soup", "cuisine": "french", "diet": ["vegan", "dairy-free", "gluten-free"], "meal_type": ["dinner", "appetizer"], "prep_time": 30, "difficulty": "medium", "ingredients": ["mushroom", "onion", "garlic", "coconut milk", "thyme", "vegetable broth"]}
        ]

        # Filter recipes based on criteria
        filtered = []
        for recipe in recipes:
            # Check ingredient match (at least 2 ingredients must match, or all if single ingredient)
            recipe_ingredients_lower = [i.lower() for i in recipe['ingredients']]
            matches = sum(1 for ing in ingredient_list if ing in recipe_ingredients_lower or any(ing in ri for ri in recipe_ingredients_lower))
            if matches == 0:
                continue
            if len(ingredient_list) >= 2 and matches < 2:
                continue
            if len(ingredient_list) == 1 and matches == 0:
                continue

            # Cuisine filter
            if cuisine and recipe['cuisine'] != cuisine:
                continue

            # Diet filter
            if diet and diet not in recipe['diet']:
                continue

            # Meal type filter
            if meal_type and meal_type not in recipe['meal_type']:
                continue

            # Prep time filter
            if recipe['prep_time'] > max_prep_time:
                continue

            # Calculate relevance score based on ingredient match ratio
            relevance = matches / len(ingredient_list)
            filtered.append({**recipe, 'relevance': relevance})

        # Sort results
        if sort_by == 'prep_time_asc':
            filtered.sort(key=lambda r: r['prep_time'])
        elif sort_by == 'prep_time_desc':
            filtered.sort(key=lambda r: r['prep_time'], reverse=True)
        elif sort_by == 'difficulty_easiest':
            diff_order = {'easy': 0, 'medium': 1, 'hard': 2}
            filtered.sort(key=lambda r: diff_order.get(r['difficulty'], 1))
        elif sort_by == 'difficulty_hardest':
            diff_order = {'easy': 2, 'medium': 1, 'hard': 0}
            filtered.sort(key=lambda r: diff_order.get(r['difficulty'], 1))
        else:  # relevance
            filtered.sort(key=lambda r: r['relevance'], reverse=True)

        # Limit results
        filtered = filtered[:max_results]

        if not filtered:
            return json.dumps({"recipes": [], "message": "No recipes found matching your criteria. Try different ingredients or relax your filters."}, ensure_ascii=False)

        # Format results
        results = []
        for r in filtered:
            results.append({
                "name": r['name'],
                "cuisine": r['cuisine'],
                "diet": r['diet'],
                "meal_type": r['meal_type'],
                "prep_time_minutes": r['prep_time'],
                "difficulty": r['difficulty'],
                "key_ingredients": r['ingredients'][:5],
                "match_score": round(r['relevance'] * 100)
            })

        return json.dumps({
            "recipes": results,
            "total_found": len(results),
            "search_parameters": {
                "ingredients": ingredient_list,
                "cuisine": cuisine if cuisine else "any",
                "diet": diet if diet else "any",
                "meal_type": meal_type if meal_type else "any",
                "max_prep_time": max_prep_time
            }
        }, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "recipe_search",
    "description": "Search for recipes by ingredient, cuisine type, dietary preference, or meal type. Returns matching recipe names, estimated prep time, difficulty level, and key ingredients.",
    "category": "search",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "ingredients": {
            "type": "string",
            "description": "Comma-separated list of ingredients to search for, e.g. 'chicken, rice, broccoli'"
        },
        "cuisine": {
            "type": "string",
            "description": "Optional: Filter by cuisine type. Supported values: italian, mexican, chinese, japanese, indian, french, american, thai, greek, mediterranean, korean, vietnamese",
            "enum": [
                "italian",
                "mexican",
                "chinese",
                "japanese",
                "indian",
                "french",
                "american",
                "thai",
                "greek",
                "mediterranean",
                "korean",
                "vietnamese"
            ]
        },
        "diet": {
            "type": "string",
            "description": "Optional: Filter by dietary preference. Supported values: vegetarian, vegan, gluten-free, dairy-free, keto, paleo, low-carb, low-fat, high-protein",
            "enum": [
                "vegetarian",
                "vegan",
                "gluten-free",
                "dairy-free",
                "keto",
                "paleo",
                "low-carb",
                "low-fat",
                "high-protein"
            ]
        },
        "meal_type": {
            "type": "string",
            "description": "Optional: Filter by meal type. Supported values: breakfast, lunch, dinner, dessert, snack, appetizer, side",
            "enum": [
                "breakfast",
                "lunch",
                "dinner",
                "dessert",
                "snack",
                "appetizer",
                "side"
            ]
        },
        "max_prep_time": {
            "type": "integer",
            "description": "Optional: Maximum preparation time in minutes (e.g. 30 for recipes under 30 minutes)",
            "minimum": 1,
            "maximum": 480
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of recipes to return. Default is 10. Range 1-50",
            "default": 10,
            "minimum": 1,
            "maximum": 50
        },
        "sort_by": {
            "type": "string",
            "description": "Optional: Sort results by criteria. Supported values: relevance (default), prep_time_asc, prep_time_desc, difficulty_easiest, difficulty_hardest",
            "enum": [
                "relevance",
                "prep_time_asc",
                "prep_time_desc",
                "difficulty_easiest",
                "difficulty_hardest"
            ],
            "default": "relevance"
        }
    },
    "required": [
        "ingredients"
    ]
},
}
