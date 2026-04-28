"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        ingredient = data.get('ingredient', '').strip().lower()
        diet = data.get('diet', 'omnivore').strip().lower()
        purpose = data.get('purpose', 'cooking').strip().lower()
        available_only = data.get('available_only', False)

        if not ingredient:
            return json.dumps({'error': 'Ingredient name is required.'}, ensure_ascii=False)

        # Substitution knowledge base
        substitutions = {
            'butter': {
                'baking': [
                    {'substitute': 'coconut oil', 'compatibility': 0.8, 'notes': 'Use 1:1 ratio, may add coconut flavor'},
                    {'substitute': 'applesauce', 'compatibility': 0.7, 'notes': 'Use 1/2 cup applesauce per 1 cup butter, reduce sugar'},
                    {'substitute': 'mashed banana', 'compatibility': 0.6, 'notes': 'Use 1/2 cup banana per 1 cup butter, adds sweetness'},
                    {'substitute': 'vegan butter', 'compatibility': 0.9, 'notes': 'Direct 1:1 swap'},
                    {'substitute': 'ghee', 'compatibility': 0.85, 'notes': 'Dairy-free, 1:1 ratio'}
                ],
                'cooking': [
                    {'substitute': 'olive oil', 'compatibility': 0.9, 'notes': 'Use 3/4 cup oil per 1 cup butter'},
                    {'substitute': 'coconut oil', 'compatibility': 0.85, 'notes': '1:1 ratio, use refined for neutral flavor'},
                    {'substitute': 'avocado oil', 'compatibility': 0.8, 'notes': 'High smoke point, 1:1 ratio'}
                ]
            },
            'eggs': {
                'baking': [
                    {'substitute': 'flax egg', 'compatibility': 0.85, 'notes': '1 tbsp flaxseed meal + 2.5 tbsp water per egg'},
                    {'substitute': 'chia egg', 'compatibility': 0.8, 'notes': '1 tbsp chia seeds + 2.5 tbsp water per egg'},
                    {'substitute': 'applesauce', 'compatibility': 0.7, 'notes': '1/4 cup applesauce per egg'},
                    {'substitute': 'mashed banana', 'compatibility': 0.75, 'notes': '1/4 cup banana per egg, adds sweetness'},
                    {'substitute': 'commercial egg replacer', 'compatibility': 0.9, 'notes': 'Follow package instructions'}
                ],
                'binding': [
                    {'substitute': 'flax egg', 'compatibility': 0.9, 'notes': 'Works well for burgers or meatballs'},
                    {'substitute': 'breadcrumbs', 'compatibility': 0.8, 'notes': '2 tbsp per egg, may change texture'},
                    {'substitute': 'rolled oats', 'compatibility': 0.75, 'notes': '1/4 cup ground oats per egg'}
                ]
            },
            'milk': {
                'baking': [
                    {'substitute': 'almond milk', 'compatibility': 0.85, 'notes': '1:1 ratio, use unsweetened'},
                    {'substitute': 'soy milk', 'compatibility': 0.9, 'notes': '1:1 ratio, similar protein content'},
                    {'substitute': 'oat milk', 'compatibility': 0.85, 'notes': '1:1 ratio, creamy texture'},
                    {'substitute': 'coconut milk', 'compatibility': 0.7, 'notes': 'Thicker, use 1:1 ratio for rich recipes'}
                ],
                'cooking': [
                    {'substitute': 'water', 'compatibility': 0.5, 'notes': 'Use same amount, less creamy'},
                    {'substitute': 'broth (vegetable/chicken)', 'compatibility': 0.6, 'notes': 'Savory dishes only'}
                ]
            },
            'sugar': {
                'baking': [
                    {'substitute': 'honey', 'compatibility': 0.8, 'notes': 'Use 3/4 cup honey per cup sugar, reduce liquid slightly'},
                    {'substitute': 'maple syrup', 'compatibility': 0.8, 'notes': 'Use 3/4 cup syrup per cup sugar'},
                    {'substitute': 'coconut sugar', 'compatibility': 0.85, 'notes': '1:1 ratio, less sweet'},
                    {'substitute': 'stevia', 'compatibility': 0.6, 'notes': 'Follow conversion on package, may have aftertaste'}
                ],
                'flavoring': [
                    {'substitute': 'vanilla extract', 'compatibility': 0.3, 'notes': 'Not a direct substitute, adds flavor only'}
                ]
            },
            'flour': {
                'baking': [
                    {'substitute': 'almond flour', 'compatibility': 0.7, 'notes': 'Low carb, 1:1 ratio for some recipes, more moisture'},
                    {'substitute': 'coconut flour', 'compatibility': 0.6, 'notes': 'Use 1/4 cup coconut flour per cup wheat flour, add eggs'},
                    {'substitute': 'oat flour', 'compatibility': 0.8, 'notes': '1:1 ratio, grind oats in blender'},
                    {'substitute': 'gluten-free all-purpose blend', 'compatibility': 0.85, 'notes': '1:1 ratio, may need xanthan gum'}
                ]
            },
            'cheese': {
                'cooking': [
                    {'substitute': 'nutritional yeast', 'compatibility': 0.7, 'notes': 'For vegan cheese flavor, 1-2 tbsp per cup'},
                    {'substitute': 'vegan cheese shreds', 'compatibility': 0.8, 'notes': 'Meltable, 1:1 ratio'},
                    {'substitute': 'tofu blended with garlic and lemon', 'compatibility': 0.6, 'notes': 'For ricotta-style substitute'}
                ]
            }
        }

        # Dietary restrictions filter
        diet_restrictions = {
            'vegan': ['honey', 'ghee', 'cheese', 'egg', 'milk', 'butter', 'cream'],
            'dairy_free': ['butter', 'milk', 'cheese', 'cream', 'ghee'],
            'gluten_free': ['flour', 'breadcrumbs', 'pasta', 'soy sauce'],
            'low_carb': ['sugar', 'flour', 'rice', 'pasta', 'breadcrumbs', 'applesauce', 'banana', 'honey', 'maple syrup'],
            'keto': ['sugar', 'flour', 'rice', 'pasta', 'breadcrumbs', 'applesauce', 'banana', 'honey', 'maple syrup', 'milk'],
            'paleo': ['milk', 'cheese', 'butter', 'cream', 'tofu', 'breadcrumbs', 'soy sauce'],
            'vegetarian': [],
            'omnivore': []
        }

        restricted_ingredients = diet_restrictions.get(diet, [])

        # Find matching substitutions
        ingredient_key = None
        for key in substitutions.keys():
            if key == ingredient or ingredient in key:
                ingredient_key = key
                break

        if not ingredient_key:
            return json.dumps({'error': f'No substitution data available for "{ingredient}".'}, ensure_ascii=False)

        purpose_key = purpose
        if purpose_key not in substitutions[ingredient_key]:
            # Fallback to first available purpose
            possible_purposes = list(substitutions[ingredient_key].keys())
            if possible_purposes:
                purpose_key = possible_purposes[0]
            else:
                return json.dumps({'error': f'No substitution data for purpose "{purpose}".'}, ensure_ascii=False)

        candidates = substitutions[ingredient_key][purpose_key]

        # Apply dietary filter
        filtered = []
        for cand in candidates:
            sub_name = cand['substitute'].lower()
            is_restricted = any(restrict in sub_name for restrict in restricted_ingredients)
            if not is_restricted:
                # Check if substitute itself is restricted (simplified)
                # For low_carb/keto, restrict sugars and fruits
                if diet in ['low_carb', 'keto']:
                    if sub_name in ['honey', 'maple syrup', 'applesauce', 'banana', 'coconut sugar', 'stevia']:
                        continue
                if diet == 'paleo' and sub_name in ['tofu', 'vegan butter', 'vegan cheese', 'commercial egg replacer', 'breadcrumbs']:
                    continue
                filtered.append(cand)

        if not filtered:
            # Fallback to original candidates with warning
            filtered = [{'substitute': 'No perfect match', 'compatibility': 0.0, 'notes': 'Consider different purpose or ingredient'}] 

        # If available_only, filter to common pantry items
        if available_only:
            pantry = ['water', 'oil', 'salt', 'sugar', 'honey', 'flour', 'eggs', 'milk', 'butter', 'applesauce', 'banana', 'lemon', 'garlic', 'oats', 'breadcrumbs', 'vanilla', 'cinnamon']
            filtered = [c for c in filtered if any(pantry_item in c['substitute'].lower() for pantry_item in pantry)]
            if not filtered:
                filtered = [{'substitute': 'No pantry item found', 'compatibility': 0.0, 'notes': 'Try available_only=false for more options'}]

        result = {
            'ingredient': ingredient,
            'diet': diet,
            'purpose': purpose,
            'substitutions': sorted(filtered, key=lambda x: x['compatibility'], reverse=True),
            'recommendation': filtered[0] if filtered else None
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "ingredient_substitution",
    "description": "Suggest suitable ingredient substitutes based on dietary restrictions, availability, and cooking purpose, returning a list of alternatives with compatibility scores and usage notes.",
    "category": "analysis",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "ingredient": {
            "type": "string",
            "description": "Name of the ingredient to substitute (e.g., 'butter', 'eggs')."
        },
        "diet": {
            "type": "string",
            "enum": [
                "omnivore",
                "vegetarian",
                "vegan",
                "gluten_free",
                "dairy_free",
                "low_carb",
                "keto",
                "paleo"
            ],
            "description": "Dietary preference or restriction to guide substitution options."
        },
        "purpose": {
            "type": "string",
            "enum": [
                "baking",
                "cooking",
                "thickening",
                "binding",
                "leavening",
                "flavoring",
                "texture"
            ],
            "description": "Cooking or baking purpose the substitute must fulfill."
        },
        "available_only": {
            "type": "boolean",
            "description": "Optional: If true, only suggest substitutes from a common household pantry (default false)."
        }
    },
    "required": [
        "ingredient",
        "diet",
        "purpose"
    ]
},
}
