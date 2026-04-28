"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a unique fusion recipe combining elements from two cultures."""
    import json
    import random

    try:
        data = json.loads(payload)
        culture_a = data.get('culture_a')
        culture_b = data.get('culture_b')
        course_type = data.get('course_type', 'main_course')
        difficulty = data.get('difficulty', 'medium')
        max_prep = data.get('max_prep_time_minutes')
        dietary = data.get('dietary_restrictions', [])

        if not culture_a or not culture_b:
            return json.dumps({'error': 'Both culture_a and culture_b are required.'}, ensure_ascii=False)

        # Generate a recipe name by combining elements from both cultures
        culture_adjectives = {
            'italian': 'Rustic', 'japanese': 'Umami', 'mexican': 'Zesty',
            'indian': 'Aromatic', 'thai': 'Fragrant', 'french': 'Sophisticated',
            'chinese': 'Harmonious', 'american': 'Hearty', 'greek': 'Mediterranean',
            'korean': 'Bold', 'moroccan': 'Spiced', 'ethiopian': 'Earthy'
        }
        adj_a = culture_adjectives.get(culture_a.lower(), 'Creative')
        adj_b = culture_adjectives.get(culture_b.lower(), 'Inspired')
        random_suffix = random.choice(['Melt', 'Fusion', 'Delight', 'Collab', 'Harmony', 'Ensemble'])
        recipe_name = f'{adj_a} {adj_b} {random_suffix}'

        # Generate cultural synopsis
        synopsis = f"This {difficulty} {course_type.replace('_', ' ')} combines the {adj_a.lower()} flavors of {culture_a} cuisine with the {adj_b.lower()} techniques of {culture_b} cuisine, creating a unique cross-cultural dining experience."

        # Build ingredient list based on cultures and dietary restrictions
        base_ingredients = {
            'italian': ['olive oil', 'parmesan', 'basil', 'tomato', 'garlic', 'mozzarella', 'pasta', 'oregano'],
            'japanese': ['soy sauce', 'mirin', 'sesame oil', 'nori', 'rice', 'tofu', 'miso', 'wasabi'],
            'mexican': ['avocado', 'lime', 'cilantro', 'corn tortilla', 'beans', 'chili', 'cumin', 'coriander'],
            'indian': ['ghee', 'cumin', 'turmeric', 'cardamom', 'coconut milk', 'lentils', 'naan', 'garam masala'],
            'thai': ['coconut milk', 'lemongrass', 'galangal', 'fish sauce', 'kaffir lime', 'chili', 'basil', 'rice noodles'],
            'french': ['butter', 'cream', 'dijon mustard', 'thyme', 'shallot', 'baguette', 'wine', 'gruyere'],
            'chinese': ['soy sauce', 'ginger', 'scallion', 'soybean paste', 'rice', 'oyster sauce', 'sesame', 'five spice'],
            'american': ['bacon', 'cheddar', 'potato', 'ketchup', 'ground beef', 'lettuce', 'bread', 'sour cream'],
            'korean': ['gochujang', 'kimchi', 'soy sauce', 'sesame oil', 'garlic', 'rice', 'tofu', 'scallion'],
            'moroccan': ['cumin', 'cinnamon', 'saffron', 'olive oil', 'couscous', 'chickpeas', 'raisins', 'almonds'],
            'ethiopian': ['berbere spice', 'niter kibbeh', 'teff', 'lentils', 'onion', 'garlic', 'ginger', 'tomato']
        }

        ingredients_a = base_ingredients.get(culture_a.lower(), ['seasonal produce', 'local spices'])
        ingredients_b = base_ingredients.get(culture_b.lower(), ['fresh herbs', 'grains'])

        # Filter out ingredients that conflict with dietary restrictions
        forbidden_map = {
            'vegetarian': ['bacon', 'ground beef', 'fish sauce', 'chicken'],
            'vegan': ['bacon', 'ground beef', 'fish sauce', 'chicken', 'butter', 'cream', 'cheese', 'mozzarella', 'parmesan', 'ghee', 'egg', 'honey'],
            'gluten-free': ['pasta', 'baguette', 'bread', 'naan', 'couscous', 'tortilla'],
            'nut-free': ['almonds', 'cashew', 'peanut', 'pistachio', 'walnut']
        }

        def filter_ingredients(ing_list):
            filtered = []
            for ing in ing_list:
                forbidden = False
                for restriction in dietary:
                    r = restriction.lower().strip()
                    if r in forbidden_map and ing.lower() in forbidden_map[r]:
                        forbidden = True
                        break
                if not forbidden:
                    filtered.append(ing)
            return filtered

        ingredients_a = filter_ingredients(ingredients_a)
        ingredients_b = filter_ingredients(ingredients_b)

        # Pick a subset for the recipe
        num_ingredients = random.randint(4, min(6, len(ingredients_a)))
        chosen_a = random.sample(ingredients_a, num_ingredients) if len(ingredients_a) >= num_ingredients else ingredients_a
        num_ingredients_b = random.randint(4, min(6, len(ingredients_b)))
        chosen_b = random.sample(ingredients_b, num_ingredients_b) if len(ingredients_b) >= num_ingredients_b else ingredients_b

        all_ingredients = list(set(chosen_a + chosen_b))
        random.shuffle(all_ingredients)

        # Add substitutions for dietary restrictions if any
        substitutions = {}
        if 'vegetarian' in [r.lower() for r in dietary] or 'vegan' in [r.lower() for r in dietary]:
            substitutions['protein_option'] = 'tofu, tempeh, or seitan'
        if 'gluten-free' in [r.lower() for r in dietary]:
            substitutions['grain_option'] = 'quinoa, rice, or gluten-free pasta'

        # Generate step-by-step instructions
        prep_time = random.randint(10, 30) if difficulty == 'easy' else (random.randint(30, 60) if difficulty == 'medium' else random.randint(60, 120))
        cook_time = random.randint(10, 20) if difficulty == 'easy' else (random.randint(20, 40) if difficulty == 'medium' else random.randint(40, 90))
        total_time = prep_time + cook_time

        if max_prep and total_time > max_prep:
            # Scale down to fit
            scale = max_prep / total_time
            prep_time = max(10, int(prep_time * scale))
            cook_time = max(10, int(cook_time * scale))
            total_time = prep_time + cook_time

        steps = [
            f"Step 1: Prepare all ingredients — {', '.join(all_ingredients[:min(4, len(all_ingredients))])} and others as listed.",
            f"Step 2: In a large {random.choice(['bowl', 'pan', 'pot', 'skillet'])}, combine the {culture_a.lower()} elements and {random.choice(['marinate', 'season', 'mix', 'layer'])} for {prep_time} minutes.",
            f"Step 3: Incorporate the {culture_b.lower()} techniques — {random.choice(['fold', 'whip', 'steam', 'grill', 'simmer'])} the mixture gently.",
            f"Step 4: Cook for approximately {cook_time} minutes over {random.choice(['medium', 'low', 'medium-high'])} heat until {random.choice(['golden', 'fragrant', 'tender', 'bubbling'])}.",
            f"Step 5: Garnish with {random.choice(['fresh herbs', 'a squeeze of citrus', 'toasted seeds', 'a drizzle of sauce'])} and serve immediately.",
            f"Step 6: Enjoy your {recipe_name} — a fusion of {culture_a} and {culture_b} traditions!"
        ]

        result = {
            'recipe_name': recipe_name,
            'cultural_synopsis': synopsis,
            'course_type': course_type.replace('_', ' '),
            'difficulty': difficulty,
            'prep_time_minutes': prep_time,
            'cook_time_minutes': cook_time,
            'total_time_minutes': total_time,
            'ingredients': all_ingredients,
            'substitutions': substitutions if substitutions else None,
            'instructions': steps,
            'dietary_notes': f'Recipe accommodates: {", ".join(dietary) if dietary else "No specific restrictions"}'
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "cultural_fusion_recipe",
    "description": "Generate a unique fusion recipe that combines culinary elements from two distinct cultures or traditions, including a synopsis of the cultural inspiration, a list of ingredients with possible substitutions, step-by-step cooking instructions, and estimated preparation time.",
    "category": "generate",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "culture_a": {
            "type": "string",
            "description": "The primary culture or cuisine tradition (e.g., Italian, Japanese, Mexican, Indian).",
            "examples": [
                "Italian",
                "Thai"
            ]
        },
        "culture_b": {
            "type": "string",
            "description": "The secondary culture or cuisine tradition to fuse with the first.",
            "examples": [
                "Japanese",
                "Mexican"
            ]
        },
        "course_type": {
            "type": "string",
            "description": "Optional: Type of dish desired (appetizer, main course, dessert, snack, or whole_meal). If omitted, defaults to main_course.",
            "enum": [
                "appetizer",
                "main_course",
                "dessert",
                "snack",
                "whole_meal"
            ],
            "default": "main_course"
        },
        "difficulty": {
            "type": "string",
            "description": "Optional: Desired cooking difficulty level (easy, medium, hard). If omitted, defaults to medium.",
            "enum": [
                "easy",
                "medium",
                "hard"
            ],
            "default": "medium"
        },
        "max_prep_time_minutes": {
            "type": "integer",
            "description": "Optional: Maximum total preparation and cooking time in minutes. If omitted, no time limit is applied.",
            "minimum": 10,
            "maximum": 480
        },
        "dietary_restrictions": {
            "type": "array",
            "description": "Optional: List of dietary restrictions or preferences to accommodate (e.g., vegetarian, vegan, gluten-free, nut-free).",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "culture_a",
        "culture_b"
    ]
},
}
