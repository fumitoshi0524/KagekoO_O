"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage a persistent shopping list by adding/removing/clearing/listing items."""
    import json
    import os
    
    try:
        data = json.loads(payload)
        action = data.get('action')
        
        if action not in ['add', 'remove', 'clear', 'list']:
            return json.dumps({'error': f'Invalid action: {action}. Must be add, remove, clear, or list.'})
        
        list_file = os.path.join(os.path.expanduser('~'), '.shopping_list.json')
        
        # Load existing list or create empty
        if os.path.exists(list_file):
            with open(list_file, 'r', encoding='utf-8') as f:
                try:
                    shopping_list = json.load(f)
                except:
                    shopping_list = []
        else:
            shopping_list = []
        
        if action == 'add':
            item_name = data.get('item_name')
            if not item_name:
                return json.dumps({'error': 'item_name is required for add action.'})
            quantity = data.get('quantity', 1)
            unit = data.get('unit', 'pieces')
            # Check if item already exists, update quantity
            found = False
            for item in shopping_list:
                if item['name'].lower() == item_name.lower():
                    item['quantity'] += quantity
                    found = True
                    break
            if not found:
                shopping_list.append({
                    'name': item_name,
                    'quantity': quantity,
                    'unit': unit
                })
            message = f'Added {quantity} {unit} of {item_name} to shopping list.'
        
        elif action == 'remove':
            item_name = data.get('item_name')
            if not item_name:
                return json.dumps({'error': 'item_name is required for remove action.'})
            initial_len = len(shopping_list)
            shopping_list = [item for item in shopping_list if item['name'].lower() != item_name.lower()]
            if len(shopping_list) < initial_len:
                message = f'Removed {item_name} from shopping list.'
            else:
                message = f'Item {item_name} not found in shopping list.'
        
        elif action == 'clear':
            shopping_list = []
            message = 'Shopping list has been cleared.'
        
        elif action == 'list':
            message = 'Current shopping list retrieved.'
        
        # Save updated list
        with open(list_file, 'w', encoding='utf-8') as f:
            json.dump(shopping_list, f, indent=2, ensure_ascii=False)
        
        return json.dumps({
            'success': True,
            'message': message,
            'shopping_list': shopping_list,
            'item_count': len(shopping_list)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({'error': f'Failed to process request: {str(e)}'})


TOOL_SPEC = {
    "name": "shopping_list_manager",
    "description": "Manage a persistent shopping list by adding items with optional quantities, removing items, clearing the entire list, or retrieving the current list of items. Returns the updated shopping list as a structured JSON array.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The operation to perform on the shopping list: add (add a new item), remove (remove an existing item), clear (delete all items), or list (get current items).",
            "enum": [
                "add",
                "remove",
                "clear",
                "list"
            ],
            "examples": [
                "add",
                "remove",
                "clear",
                "list"
            ]
        },
        "item_name": {
            "type": "string",
            "description": "Optional: The name of the item to add or remove. Required when action is 'add' or 'remove'.",
            "minLength": 1,
            "maxLength": 200,
            "examples": [
                "milk",
                "bread",
                "eggs"
            ]
        },
        "quantity": {
            "type": "integer",
            "description": "Optional: The quantity of the item to add. Defaults to 1 if not specified. Only used when action is 'add'.",
            "minimum": 1,
            "maximum": 1000,
            "examples": [
                2,
                5,
                1
            ]
        },
        "unit": {
            "type": "string",
            "description": "Optional: The unit of measurement for the item (e.g., 'liters', 'pieces', 'kg'). Only used when action is 'add'.",
            "maxLength": 50,
            "examples": [
                "liters",
                "pieces",
                "kg",
                "bottles"
            ]
        }
    },
    "required": [
        "action"
    ]
},
}
