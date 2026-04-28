"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        orig = data['original_servings']
        target = data['target_servings']
        factor = target / orig
        scaled = []
        for ing in data['ingredients']:
            scaled_qty = round(ing['quantity'] * factor, 2)
            scaled.append({
                'name': ing['name'],
                'original_quantity': ing['quantity'],
                'unit': ing['unit'],
                'scaled_quantity': scaled_qty
            })
        result = {
            'original_servings': orig,
            'target_servings': target,
            'scale_factor': factor,
            'scaled_ingredients': scaled
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "recipe_scaler",
    "description": "Scale ingredient quantities in a cooking recipe by a given multiplier (e.g., double, halve, or triple servings) and return the adjusted ingredient list along with the new serving count.",
    "category": "operations",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "original_servings": {
            "type": "integer",
            "description": "The number of servings the original recipe makes.",
            "minimum": 1
        },
        "target_servings": {
            "type": "integer",
            "description": "The desired number of servings after scaling.",
            "minimum": 1
        },
        "ingredients": {
            "type": "array",
            "description": "List of ingredients with their original quantities and units.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the ingredient (e.g., 'flour', 'sugar')."
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Original quantity as a decimal number (e.g., 1.5 for 1.5 cups).",
                        "minimum": 0
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measurement (e.g., 'cups', 'tablespoons', 'grams', 'pieces')."
                    }
                },
                "required": [
                    "name",
                    "quantity",
                    "unit"
                ]
            },
            "minItems": 1
        }
    },
    "required": [
        "original_servings",
        "target_servings",
        "ingredients"
    ]
},
}
