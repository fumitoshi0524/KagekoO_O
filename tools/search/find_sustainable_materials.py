"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for sustainable materials by name/category and return matching records with environmental ratings, recyclability, lifecycle stage, and certifications."""
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip().lower()
        if not query:
            return json.dumps({'error': 'query is required', 'results': []}, ensure_ascii=False)
        
        category = data.get('category', 'all')
        min_rating = data.get('min_rating', 0)
        cert = data.get('certification', 'any')
        
        # Simulated database of sustainable materials
        materials = [
            {'name': 'Bamboo Fiber', 'category': 'textiles', 'rating': 8.5, 'recyclable': True, 'lifecycle': 'renewable', 'certifications': ['FSC']},
            {'name': 'Recycled PET Plastic', 'category': 'packaging', 'rating': 7.2, 'recyclable': True, 'lifecycle': 'recycled', 'certifications': ['Cradle_to_Cradle']},
            {'name': 'Hempcrete', 'category': 'construction', 'rating': 9.1, 'recyclable': False, 'lifecycle': 'biodegradable', 'certifications': []},
            {'name': 'Mycelium Packaging', 'category': 'packaging', 'rating': 9.8, 'recyclable': True, 'lifecycle': 'compostable', 'certifications': ['EU_Ecolabel']},
            {'name': 'Recycled Aluminum', 'category': 'electronics', 'rating': 8.0, 'recyclable': True, 'lifecycle': 'recycled', 'certifications': ['Energy_Star']},
            {'name': 'Organic Cotton', 'category': 'textiles', 'rating': 7.8, 'recyclable': True, 'lifecycle': 'renewable', 'certifications': ['EU_Ecolabel']},
            {'name': 'Straw Bale', 'category': 'construction', 'rating': 9.5, 'recyclable': False, 'lifecycle': 'biodegradable', 'certifications': []},
            {'name': 'Bioplastic (PLA)', 'category': 'packaging', 'rating': 6.0, 'recyclable': False, 'lifecycle': 'compostable', 'certifications': ['Cradle_to_Cradle']},
            {'name': 'Recycled Copper', 'category': 'electronics', 'rating': 7.5, 'recyclable': True, 'lifecycle': 'recycled', 'certifications': []},
        ]
        
        results = []
        for m in materials:
            if query not in m['name'].lower():
                continue
            if category != 'all' and m['category'] != category:
                continue
            if m['rating'] < min_rating:
                continue
            if cert != 'any' and cert not in m['certifications']:
                continue
            results.append(m)
        
        return json.dumps({'query': query, 'count': len(results), 'results': results}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "find_sustainable_materials",
    "description": "Search for sustainable and eco-friendly materials by name or category, returning matching materials with their environmental impact ratings, recyclability, lifecycle stage, and certifications.",
    "category": "search",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search query for material name or category (e.g., 'bamboo', 'recycled plastic', 'biodegradable packaging')."
        },
        "category": {
            "type": "string",
            "enum": [
                "packaging",
                "construction",
                "textiles",
                "electronics",
                "all"
            ],
            "description": "Optional: Filter search by material application category. Default 'all' searches across all categories."
        },
        "min_rating": {
            "type": "number",
            "minimum": 0,
            "maximum": 10,
            "description": "Optional: Minimum environmental impact rating (0-10, 10 being best). Filters results to materials with rating >= this value."
        },
        "certification": {
            "type": "string",
            "enum": [
                "FSC",
                "Cradle_to_Cradle",
                "Energy_Star",
                "EU_Ecolabel",
                "any"
            ],
            "description": "Optional: Filter by specific sustainability certification. Default 'any' returns materials with any or no certification."
        }
    },
    "required": [
        "query"
    ]
},
}
