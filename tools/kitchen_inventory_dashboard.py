"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generates a structured dashboard of a user's kitchen inventory."""
    import json
    from datetime import datetime, date
    try:
        data = json.loads(payload)
        items = data.get('items', [])
        if not items:
            return json.dumps({"error": "items list cannot be empty", "dashboard": {}}, ensure_ascii=False)
        
        sort_by = data.get('sort_by', 'category_expiry')
        include_alerts = data.get('include_low_stock_alerts', True)
        
        today = date.today()
        dashboard = {
            "generated_at": today.isoformat(),
            "total_items": len(items),
            "categories": {},
            "alerts": []
        }
        
        # Precompute freshness and expiry info
        enriched = []
        for item in items:
            try:
                purchase = datetime.strptime(item['purchase_date'], '%Y-%m-%d').date()
                expiry = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
            except ValueError:
                continue
            
            days_until_expiry = (expiry - today).days
            total_shelf_life = (expiry - purchase).days
            freshness_pct = max(0, min(100, ((today - purchase).days / total_shelf_life) * 100)) if total_shelf_life > 0 else 0
            
            # Low stock threshold: assume 5 units as typical full stock for simplicity
            typical_full = 5.0
            low_stock_threshold = typical_full * 0.2
            is_low_stock = item['quantity'] < low_stock_threshold if include_alerts else False
            
            status = "fresh" if days_until_expiry > 7 else ("expiring_soon" if days_until_expiry >= 0 else "expired")
            
            enriched_item = {
                "name": item['name'].lower(),
                "category": item['category'],
                "quantity": item['quantity'],
                "quantity_unit": item['quantity_unit'],
                "purchase_date": item['purchase_date'],
                "expiry_date": item['expiry_date'],
                "days_until_expiry": days_until_expiry,
                "freshness_percentage": round(freshness_pct, 1),
                "status": status,
                "low_stock": is_low_stock
            }
            enriched.append(enriched_item)
        
        # Sort
        if sort_by == 'category_expiry':
            enriched.sort(key=lambda x: (x['category'], x['days_until_expiry']))
        elif sort_by == 'expiry_asc':
            enriched.sort(key=lambda x: x['days_until_expiry'])
        elif sort_by == 'name_asc':
            enriched.sort(key=lambda x: x['name'])
        elif sort_by == 'freshness_desc':
            enriched.sort(key=lambda x: -x['freshness_percentage'])
        
        # Build category groups
        for item in enriched:
            cat = item['category']
            if cat not in dashboard['categories']:
                dashboard['categories'][cat] = {
                    "items": [],
                    "count": 0,
                    "expired_count": 0,
                    "expiring_soon_count": 0
                }
            dashboard['categories'][cat]['items'].append(item)
            dashboard['categories'][cat]['count'] += 1
            if item['status'] == 'expired':
                dashboard['categories'][cat]['expired_count'] += 1
            elif item['status'] == 'expiring_soon':
                dashboard['categories'][cat]['expiring_soon_count'] += 1
            
            if item['low_stock']:
                dashboard['alerts'].append({
                    "type": "low_stock",
                    "item": item['name'],
                    "current_quantity": f"{item['quantity']} {item['quantity_unit']}",
                    "message": f"Low stock: only {item['quantity']} {item['quantity_unit']} of {item['name']} remaining."
                })
            if item['status'] == 'expired':
                dashboard['alerts'].append({
                    "type": "expired",
                    "item": item['name'],
                    "expiry_date": item['expiry_date'],
                    "message": f"{item['name']} expired on {item['expiry_date']}. Please discard."
                })
            elif item['status'] == 'expiring_soon':
                dashboard['alerts'].append({
                    "type": "expiring_soon",
                    "item": item['name'],
                    "days_left": item['days_until_expiry'],
                    "message": f"{item['name']} expires in {item['days_until_expiry']} days. Use it soon!"
                })
        
        # Compute overall stats
        total_expired = sum(cat['expired_count'] for cat in dashboard['categories'].values())
        total_expiring = sum(cat['expiring_soon_count'] for cat in dashboard['categories'].values())
        dashboard['summary'] = {
            "total_categories": len(dashboard['categories']),
            "total_items": len(enriched),
            "expired_items": total_expired,
            "expiring_soon_items": total_expiring,
            "alerts_count": len(dashboard['alerts'])
        }
        
        return json.dumps(dashboard, ensure_ascii=False, default=str)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "kitchen_inventory_dashboard",
    "description": "Generates a structured dashboard of a user's kitchen inventory by categorizing items (pantry, fridge, freezer, spices) and annotating freshness, quantity status, and estimated days until expiry. Returns a nested JSON object suitable for rendering in a visual dashboard UI.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "description": "List of food items currently in the kitchen, each with name, category, quantity, purchase_date, and expiry_date.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the food item (e.g. 'Milk', 'Chicken breast', 'Basmati rice'). Case-insensitive, max 100 characters."
                    },
                    "category": {
                        "type": "string",
                        "description": "Storage category of the item.",
                        "enum": [
                            "pantry",
                            "fridge",
                            "freezer",
                            "spices"
                        ]
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Current remaining quantity in standard units (e.g. liters, kilograms, count). Must be positive."
                    },
                    "quantity_unit": {
                        "type": "string",
                        "description": "Unit of measurement for the quantity.",
                        "enum": [
                            "liters",
                            "kilograms",
                            "grams",
                            "pieces",
                            "bottles",
                            "cans",
                            "jars",
                            "packs"
                        ]
                    },
                    "purchase_date": {
                        "type": "string",
                        "description": "Date when the item was purchased, in ISO 8601 format (YYYY-MM-DD). Must not be in the future."
                    },
                    "expiry_date": {
                        "type": "string",
                        "description": "Best before or expiry date of the item, in ISO 8601 format (YYYY-MM-DD). Must occur after purchase_date."
                    }
                },
                "required": [
                    "name",
                    "category",
                    "quantity",
                    "quantity_unit",
                    "purchase_date",
                    "expiry_date"
                ]
            }
        },
        "sort_by": {
            "type": "string",
            "description": "Optional: Sorting criterion for the dashboard output. Default is by category then expiry.",
            "enum": [
                "category_expiry",
                "expiry_asc",
                "name_asc",
                "freshness_desc"
            ]
        },
        "include_low_stock_alerts": {
            "type": "boolean",
            "description": "Optional: If true, adds a low_stock key to each item when quantity is below a configurable threshold (default threshold: 20% of typical full stock). Default true."
        }
    },
    "required": [
        "items"
    ]
},
}
