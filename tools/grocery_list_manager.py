"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        if action not in ['add', 'remove', 'update', 'clear', 'view']:
            return json.dumps({'status': 'error', 'message': 'Invalid action. Must be add, remove, update, clear, or view.'})
        
        # Load existing list (simulated as simple file-based store)
        import os
        store_file = '/tmp/grocery_list.json'
        if os.path.exists(store_file):
            with open(store_file, 'r') as f:
                try:
                    grocery_list = json.load(f)
                except:
                    grocery_list = []
        else:
            grocery_list = []
        
        if action == 'view':
            return json.dumps({'status': 'success', 'list': grocery_list, 'message': 'Current grocery list retrieved.'}, ensure_ascii=False)
        
        if action == 'clear':
            grocery_list = []
            with open(store_file, 'w') as f:
                json.dump(grocery_list, f)
            return json.dumps({'status': 'success', 'list': [], 'message': 'Grocery list cleared.'}, ensure_ascii=False)
        
        item_name = data.get('item_name')
        if not item_name:
            return json.dumps({'status': 'error', 'message': 'item_name is required for add, remove, update actions.'})
        
        item_name = item_name.lower().strip()
        
        if action == 'add':
            quantity = data.get('quantity', 1)
            if quantity <= 0:
                return json.dumps({'status': 'error', 'message': 'Quantity must be positive.'})
            unit = data.get('unit', 'piece')
            category = data.get('category', 'other')
            # Check if item already exists, then update quantity
            found = False
            for it in grocery_list:
                if it['name'] == item_name:
                    it['quantity'] += quantity
                    found = True
                    break
            if not found:
                grocery_list.append({'name': item_name, 'quantity': quantity, 'unit': unit, 'category': category})
            with open(store_file, 'w') as f:
                json.dump(grocery_list, f)
            return json.dumps({'status': 'success', 'list': grocery_list, 'message': f'Added/updated {quantity} {unit}(s) of {item_name}.'}, ensure_ascii=False)
        
        if action == 'remove':
            # Remove item completely, or reduce quantity if specified
            quantity = data.get('quantity', None)
            found = False
            for i, it in enumerate(grocery_list):
                if it['name'] == item_name:
                    if quantity is None or quantity >= it['quantity']:
                        del grocery_list[i]
                        message = f'Removed {item_name} from list.'
                    else:
                        it['quantity'] -= quantity
                        message = f'Reduced {item_name} by {quantity}.'
                    found = True
                    break
            if not found:
                return json.dumps({'status': 'error', 'message': f'Item {item_name} not found in list.'})
            with open(store_file, 'w') as f:
                json.dump(grocery_list, f)
            return json.dumps({'status': 'success', 'list': grocery_list, 'message': message}, ensure_ascii=False)
        
        if action == 'update':
            # Update item properties
            found = False
            for it in grocery_list:
                if it['name'] == item_name:
                    if 'new_item_name' in data:
                        it['name'] = data['new_item_name'].lower().strip()
                    if 'new_quantity' in data:
                        if data['new_quantity'] <= 0:
                            return json.dumps({'status': 'error', 'message': 'New quantity must be positive.'})
                        it['quantity'] = data['new_quantity']
                    if 'new_unit' in data:
                        it['unit'] = data['new_unit']
                    if 'new_category' in data:
                        it['category'] = data['new_category']
                    found = True
                    break
            if not found:
                return json.dumps({'status': 'error', 'message': f'Item {item_name} not found.'})
            with open(store_file, 'w') as f:
                json.dump(grocery_list, f)
            return json.dumps({'status': 'success', 'list': grocery_list, 'message': f'Updated {item_name}.'}, ensure_ascii=False)
        
        return json.dumps({'status': 'error', 'message': 'Unknown error.'})
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "grocery_list_manager",
    "description": "Manages a shared grocery shopping list with add, remove, update, and clear operations for items. Each item has a name, quantity, unit, and category (produce, dairy, meat, pantry, frozen, other). Returns the current full list after each operation and confirms item changes.",
    "category": "operations",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Action to perform: add, remove, update, clear, or view",
            "enum": [
                "add",
                "remove",
                "update",
                "clear",
                "view"
            ]
        },
        "item_name": {
            "type": "string",
            "description": "Name of the grocery item (case-insensitive, e.g., 'milk', 'apples')"
        },
        "quantity": {
            "type": "number",
            "description": "Optional: Quantity of the item (must be positive number, default 1)"
        },
        "unit": {
            "type": "string",
            "description": "Optional: Unit of measurement (e.g., 'lb', 'oz', 'piece', 'bunch', 'bag', 'liter'. Default 'piece')"
        },
        "category": {
            "type": "string",
            "enum": [
                "produce",
                "dairy",
                "meat",
                "pantry",
                "frozen",
                "other"
            ],
            "description": "Optional: Category of the item. Default 'other'"
        },
        "new_item_name": {
            "type": "string",
            "description": "Optional: New name for the item when using 'update' action"
        },
        "new_quantity": {
            "type": "number",
            "description": "Optional: New quantity for the item when using 'update' action"
        },
        "new_unit": {
            "type": "string",
            "description": "Optional: New unit for the item when using 'update' action"
        },
        "new_category": {
            "type": "string",
            "enum": [
                "produce",
                "dairy",
                "meat",
                "pantry",
                "frozen",
                "other"
            ],
            "description": "Optional: New category for the item when using 'update' action"
        }
    },
    "required": [
        "action"
    ]
},
}
