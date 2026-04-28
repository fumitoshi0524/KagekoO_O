"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        if not query:
            return json.dumps({'error': 'query is required'}, ensure_ascii=False)
        category = data.get('category')
        max_price = data.get('max_price')
        min_rating = data.get('min_rating')
        sort_by = data.get('sort_by', 'relevance')
        limit = min(data.get('limit', 20), 100)

        # Simulate searching a mock competitor product database
        mock_products = [
            {'name': 'SmartWidget X1', 'category': 'electronics', 'price': 299.99, 'rating': 4.5, 'availability': 'in_stock', 'competitor': 'TechCorp'},
            {'name': 'GigaGadget Pro', 'category': 'electronics', 'price': 499.00, 'rating': 4.2, 'availability': 'low_stock', 'competitor': 'GizmoInc'},
            {'name': 'EcoMug 500ml', 'category': 'home_goods', 'price': 24.99, 'rating': 4.8, 'availability': 'in_stock', 'competitor': 'GreenHome'},
            {'name': 'ErgoChair Mesh', 'category': 'home_goods', 'price': 349.00, 'rating': 4.0, 'availability': 'out_of_stock', 'competitor': 'OfficePro'},
            {'name': 'Organic Snack Box', 'category': 'food_beverage', 'price': 15.99, 'rating': 4.6, 'availability': 'in_stock', 'competitor': 'FreshBite'}
        ]

        results = [p for p in mock_products if query.lower() in p['name'].lower()]
        if category:
            results = [p for p in results if p['category'] == category]
        if max_price is not None:
            results = [p for p in results if p['price'] <= max_price]
        if min_rating is not None:
            results = [p for p in results if p['rating'] >= min_rating]

        if sort_by == 'price_asc':
            results.sort(key=lambda x: x['price'])
        elif sort_by == 'price_desc':
            results.sort(key=lambda x: x['price'], reverse=True)
        elif sort_by == 'rating_desc':
            results.sort(key=lambda x: x['rating'], reverse=True)
        else:
            results.sort(key=lambda x: x['name'])

        results = results[:limit]
        return json.dumps({'results': results, 'count': len(results)}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "competitor_product_search",
    "description": "Search for competitor products by name, category, or price range to analyze market positioning, returns matching products with pricing, ratings, and availability.",
    "category": "search",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Product name, keyword, or phrase to search for across competitor catalogs"
        },
        "category": {
            "type": "string",
            "description": "Product category filter: electronics, clothing, home_goods, food_beverage, or other",
            "enum": [
                "electronics",
                "clothing",
                "home_goods",
                "food_beverage",
                "other"
            ]
        },
        "max_price": {
            "type": "number",
            "description": "Optional: maximum price in USD to filter results"
        },
        "min_rating": {
            "type": "number",
            "description": "Optional: minimum average rating (1.0–5.0) to filter results"
        },
        "sort_by": {
            "type": "string",
            "description": "Optional: sort order for results: price_asc, price_desc, rating_desc, or relevance",
            "enum": [
                "price_asc",
                "price_desc",
                "rating_desc",
                "relevance"
            ]
        },
        "limit": {
            "type": "integer",
            "description": "Optional: maximum number of results to return (1–100)",
            "examples": [
                10,
                25,
                50
            ]
        }
    },
    "required": [
        "query"
    ]
},
}
