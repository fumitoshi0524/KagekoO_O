"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        equipment = data.get('equipment_list', [])
        thresholds = data.get('thresholds', {})

        if not equipment:
            return json.dumps({'error': 'No equipment provided'})

        danger = thresholds.get('danger_threshold', 4)
        critical = thresholds.get('critical_threshold', 2)

        report = {
            'total_items': len(equipment),
            'needs_repair': [],
            'needs_replacement': [],
            'overdue_inspection': []
        }

        today = datetime.now().date()
        six_months_ago = today - timedelta(days=180)

        for item in equipment:
            item_id = item['id']
            item_type = item['type']
            condition = item['condition_score']
            last_insp = item['last_inspection']

            try:
                insp_date = datetime.strptime(last_insp, '%Y-%m-%d').date()
            except:
                insp_date = None

            if condition <= critical:
                report['needs_replacement'].append({
                    'id': item_id,
                    'type': item_type,
                    'condition_score': condition,
                    'reason': 'Critical condition - needs immediate replacement'
                })
            elif condition <= danger:
                report['needs_repair'].append({
                    'id': item_id,
                    'type': item_type,
                    'condition_score': condition,
                    'reason': 'Below safety threshold - needs repair'
                })

            if insp_date and insp_date < six_months_ago:
                report['overdue_inspection'].append({
                    'id': item_id,
                    'type': item_type,
                    'last_inspection': last_insp,
                    'days_since_inspection': (today - insp_date).days
                })

        report['repair_count'] = len(report['needs_repair'])
        report['replacement_count'] = len(report['needs_replacement'])
        report['overdue_inspection_count'] = len(report['overdue_inspection'])

        return json.dumps(report, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "sports_equipment_audit",
    "description": "Perform an audit of sports equipment inventory, checking availability, condition, and maintenance status of items like balls, rackets, protective gear, and fitness machines. Returns a report of items needing repair or replacement, aiding facility maintenance planning.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "equipment_list": {
            "type": "array",
            "description": "List of equipment items with their type, last inspection date, and current condition rating.",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique identifier for the equipment item."
                    },
                    "type": {
                        "type": "string",
                        "description": "Type of equipment (e.g., basketball, treadmill, helmet)."
                    },
                    "condition_score": {
                        "type": "number",
                        "description": "Condition score from 0 (poor) to 10 (excellent).",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "last_inspection": {
                        "type": "string",
                        "description": "Date of last inspection in YYYY-MM-DD format."
                    }
                },
                "required": [
                    "id",
                    "type",
                    "condition_score",
                    "last_inspection"
                ]
            }
        },
        "thresholds": {
            "type": "object",
            "description": "Optional: thresholds for condition scores to flag items for repair (danger) or replacement (critical). Default: danger < 4, critical < 2.",
            "properties": {
                "danger_threshold": {
                    "type": "number",
                    "description": "Condition score below which item is flagged for repair.",
                    "minimum": 0,
                    "maximum": 10
                },
                "critical_threshold": {
                    "type": "number",
                    "description": "Condition score below which item is flagged for immediate replacement.",
                    "minimum": 0,
                    "maximum": 10
                }
            },
            "required": []
        }
    },
    "required": [
        "equipment_list"
    ]
},
}
