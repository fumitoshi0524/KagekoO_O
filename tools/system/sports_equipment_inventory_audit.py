"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        facility_id = data.get('facility_id')
        if not facility_id:
            return json.dumps({'error': 'facility_id is required'}, ensure_ascii=False)
        check_condition = data.get('check_condition', True)
        min_stock_alert = data.get('min_stock_alert', 3)
        
        # Simulate inventory database (in real scenario, query DB)
        inventory = {
            'gym_alpha': [
                {'item': 'basketball', 'quantity': 12, 'condition': 'good', 'last_maintenance': '2024-10-15'},
                {'item': 'yoga_mat', 'quantity': 5, 'condition': 'fair', 'last_maintenance': '2023-11-20'},
                {'item': 'dumbbell_set_10kg', 'quantity': 2, 'condition': 'good', 'last_maintenance': '2024-09-01'}
            ],
            'stadium_beta': [
                {'item': 'football', 'quantity': 20, 'condition': 'excellent', 'last_maintenance': '2024-12-01'},
                {'item': 'corner_flag', 'quantity': 4, 'condition': 'good', 'last_maintenance': '2024-06-15'}
            ]
        }
        
        if facility_id not in inventory:
            return json.dumps({'error': f'facility "{facility_id}" not found'}, ensure_ascii=False)
        
        items = inventory[facility_id]
        shortages = []
        damages = []
        overdue_maintenance = []
        total_items = len(items)
        
        for item in items:
            if item['quantity'] < min_stock_alert:
                shortages.append(item)
            if check_condition and item['condition'] in ['poor', 'damaged', 'fair']:
                damages.append(item)
            # Overdue maintenance if more than 1 year since last maintenance
            from datetime import datetime, timedelta
            last_maint = datetime.strptime(item['last_maintenance'], '%Y-%m-%d')
            if datetime.now() - last_maint > timedelta(days=365):
                overdue_maintenance.append(item)
        
        result = {
            'facility_id': facility_id,
            'audit_date': datetime.now().strftime('%Y-%m-%d'),
            'total_items_checked': total_items,
            'shortages': shortages,
            'damaged_items': damages,
            'overdue_maintenance_items': overdue_maintenance,
            'summary': f'Found {len(shortages)} shortages, {len(damages)} damaged items, {len(overdue_maintenance)} overdue maintenance.'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sports_equipment_inventory_audit",
    "description": "Audit the current inventory of sports equipment items, checking stock levels, condition statuses, and maintenance schedules, and return a detailed report of all items including shortages, damaged items, and overdue maintenance tasks for the sports facility manager.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "facility_id": {
            "type": "string",
            "description": "Identifier for the sports facility (e.g., gym, stadium, training center) whose equipment inventory should be audited."
        },
        "check_condition": {
            "type": "boolean",
            "description": "Optional: If True, include detailed condition checks for each equipment item (default: True)."
        },
        "min_stock_alert": {
            "type": "integer",
            "description": "Optional: Threshold quantity below which an item is considered low stock (default: 3)."
        }
    },
    "required": [
        "facility_id"
    ]
},
}
