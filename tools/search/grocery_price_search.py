"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for grocery item prices and availability across stores."""
    import json
    try:
        data = json.loads(payload)
        item_name = data.get('item_name', '').strip()
        if not item_name:
            return json.dumps({'error': 'item_name is required and cannot be empty'}, ensure_ascii=False)
        
        category = data.get('category', None)
        store_ids = data.get('store_ids', None)
        max_price = data.get('max_price', None)
        in_stock_only = data.get('in_stock_only', False)
        
        # Simulate store database
        inventory = [
            {'store_id': 'store_001', 'store_name': 'FreshMart Downtown', 'product': 'Organic Whole Milk', 'category': 'dairy', 'unit_price': 4.99, 'in_stock': True},
            {'store_id': 'store_001', 'store_name': 'FreshMart Downtown', 'product': 'Banana (per lb)', 'category': 'produce', 'unit_price': 0.59, 'in_stock': True},
            {'store_id': 'store_002', 'store_name': 'GreenLeaf Grocery', 'product': 'Organic Whole Milk', 'category': 'dairy', 'unit_price': 5.49, 'in_stock': False},
            {'store_id': 'store_002', 'store_name': 'GreenLeaf Grocery', 'product': 'Banana (bundle)', 'category': 'produce', 'unit_price': 1.29, 'in_stock': True},
            {'store_id': 'store_003', 'store_name': 'CostSaver Foods', 'product': 'Whole Milk 1gal', 'category': 'dairy', 'unit_price': 3.99, 'in_stock': True},
        ]
        
        results = []
        query_lower = item_name.lower()
        for item in inventory:
            # Filter by store IDs if provided
            if store_ids and item['store_id'] not in store_ids:
                continue
            # Filter by category if provided
            if category and item['category'] != category:
                continue
            # Filter by price
            if max_price is not None and item['unit_price'] > max_price:
                continue
            # Filter by stock status
            if in_stock_only and not item['in_stock']:
                continue
            # Name matching (simple substring, case-insensitive)
            if query_lower in item['product'].lower():
                results.append({
                    'store_name': item['store_name'],
                    'product': item['product'],
                    'unit_price': item['unit_price'],
                    'in_stock': item['in_stock']
                })
        
        # Sort by price ascending
        results.sort(key=lambda x: x['unit_price'])
        
        return json.dumps({'results': results, 'total_count': len(results)}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "grocery_price_search",
    "description": "Search for the current price and availability of a grocery item across multiple store inventories, returning the store name, product name, unit price, and stock status for comparison and budgeting.",
    "category": "search",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "item_name": {
            "type": "string",
            "description": "Name of the grocery item to search for (e.g., 'organic whole milk', 'banana'). Max 100 characters."
        },
        "category": {
            "type": "string",
            "enum": [
                "dairy",
                "produce",
                "meat",
                "beverages",
                "bakery",
                "snacks",
                "frozen",
                "other"
            ],
            "description": "Product category to narrow the search."
        },
        "store_ids": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of specific store IDs to search (e.g., ['store_001', 'store_002']). If omitted, searches all available stores."
        },
        "max_price": {
            "type": "number",
            "description": "Optional: Maximum acceptable price (in dollars). Only return items with unit price <= this value."
        },
        "in_stock_only": {
            "type": "boolean",
            "description": "Optional: If True, only return items that are currently in stock. Default is False."
        }
    },
    "required": [
        "item_name"
    ]
},
}
