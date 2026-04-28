"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Organize a grocery list by sorting items into store sections, detecting duplicates, and estimating total cost."""
    import json
    try:
        data = json.loads(payload)
        items = data.get("items", [])
        if not items:
            return json.dumps({"error": "No items provided", "organized_list": [], "total_estimate": 0.0})
        
        # Define default store sections with keywords
        default_sections = {
            "Produce": ["apple", "banana", "orange", "lettuce", "tomato", "cucumber", "onion", "potato", "carrot", "broccoli", "spinach", "pepper", "avocado", "garlic", "ginger", "fruit", "vegetable", "herb", "salad", "mushroom"],
            "Dairy & Eggs": ["milk", "cheese", "yogurt", "butter", "cream", "egg", "sour cream", "cottage cheese"],
            "Meat & Seafood": ["chicken", "beef", "pork", "fish", "shrimp", "turkey", "sausage", "bacon", "steak", "ground beef", "lamb", "salmon", "tuna"],
            "Pantry & Dry Goods": ["rice", "pasta", "bread", "flour", "sugar", "salt", "oil", "vinegar", "sauce", "cereal", "oatmeal", "canned", "bean", "lentil", "soup", "broth"],
            "Frozen Foods": ["frozen", "ice cream", "pizza", "frozen vegetable", "frozen fruit", "frozen meal"],
            "Beverages": ["water", "juice", "soda", "coffee", "tea", "beer", "wine", "sports drink"],
            "Snacks": ["chip", "cookie", "cracker", "candy", "chocolate", "popcorn", "nut", "granola bar"],
            "Baking": ["yeast", "baking soda", "baking powder", "vanilla", "cocoa", "chocolate chip", "flour", "sugar"],
            "Condiments & Spices": ["ketchup", "mustard", "mayonnaise", "hot sauce", "soy sauce", "spice", "pepper", "salt", "garlic powder", "oregano", "basil"],
            "Household": ["paper towel", "toilet paper", "soap", "detergent", "cleaner", "sponge", "trash bag", "tissue"]
        }
        
        # Merge duplicates and categorize
        merged = {}
        for item in items:
            name = item.get("name", "").strip().lower()
            quantity = item.get("quantity", 1)
            price = item.get("estimated_price", 0)
            
            if not name:
                continue
                
            if name in merged:
                merged[name]["quantity"] += quantity
                merged[name]["total_price"] += price * quantity
            else:
                # Assign to section
                section = "Other"
                for sec_name, keywords in default_sections.items():
                    for keyword in keywords:
                        if keyword in name:
                            section = sec_name
                            break
                    if section != "Other":
                        break
                
                merged[name] = {
                    "name": item.get("name", "").strip(),
                    "quantity": quantity,
                    "unit_price": price,
                    "total_price": price * quantity,
                    "section": section
                }
        
        # Organize by section
        organized = {}
        total_cost = 0.0
        for item_name, item_data in merged.items():
            section = item_data["section"]
            if section not in organized:
                organized[section] = []
            organized[section].append({
                "name": item_data["name"],
                "quantity": item_data["quantity"],
                "unit_price": item_data["unit_price"],
                "total_price": round(item_data["total_price"], 2)
            })
            total_cost += item_data["total_price"]
        
        total_cost = round(total_cost, 2)
        
        result = {
            "organized_list": organized,
            "total_items": len(merged),
            "total_estimate": total_cost,
            "currency": "USD"
        }
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Failed to organize grocery list: {str(e)}"})


TOOL_SPEC = {
    "name": "grocery_list_organizer",
    "description": "Organize a grocery list by sorting items into store sections, detecting duplicates, and estimating total cost. Takes a list of grocery items and returns a structured list grouped by category (produce, dairy, meat, pantry, etc.) with merged quantities and a total price estimate.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "description": "List of grocery items to organize",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the grocery item"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity needed of this item",
                        "minimum": 1,
                        "default": 1
                    },
                    "estimated_price": {
                        "type": "number",
                        "description": "Estimated unit price of the item in dollars",
                        "minimum": 0
                    }
                },
                "required": [
                    "name"
                ]
            }
        },
        "store_sections": {
            "type": "array",
            "description": "Optional: Custom store section names to categorize items. Defaults to standard grocery sections.",
            "items": {
                "type": "string"
            },
            "default": [
                "Produce",
                "Dairy & Eggs",
                "Meat & Seafood",
                "Pantry & Dry Goods",
                "Frozen Foods",
                "Beverages",
                "Snacks",
                "Baking",
                "Condiments & Spices",
                "Household"
            ]
        }
    },
    "required": [
        "items"
    ]
},
}
