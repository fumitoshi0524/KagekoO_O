"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        facility_id = data.get('facility_id')
        equipment_name = data.get('equipment_name')
        last_service_date_str = data.get('last_service_date')
        condition_grade = data.get('condition_grade')
        service_interval_days = data.get('service_interval_days', 90)
        if not all([facility_id, equipment_name, last_service_date_str, condition_grade]):
            return json.dumps({'error': 'Missing required fields'}, ensure_ascii=False)
        last_service = datetime.strptime(last_service_date_str, '%Y-%m-%d')
        days_since_service = (datetime.now() - last_service).days
        overdue = days_since_service > service_interval_days
        condition_map = {'excellent': 5, 'good': 4, 'fair': 3, 'poor': 2, 'critical': 1}
        condition_score = condition_map.get(condition_grade, 0)
        needs_inspection = condition_score <= 2 or overdue
        safe_to_use = condition_score >= 3 and not overdue
        result = {
            'facility_id': facility_id,
            'equipment_name': equipment_name,
            'days_since_last_service': days_since_service,
            'service_interval_days': service_interval_days,
            'overdue': overdue,
            'condition_grade': condition_grade,
            'condition_score': condition_score,
            'needs_inspection': needs_inspection,
            'safe_to_use': safe_to_use,
            'alert': 'Equipment needs immediate inspection' if needs_inspection else 'Equipment is in good standing'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "sport_facility_maintenance_check",
    "description": "Log and verify the maintenance status of sports facility equipment (treadmills, weight machines, basketball hoops, etc.) by checking last service date, current condition grade, and expected service interval, returning a maintenance alert or confirmation that the equipment is safe to use.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "facility_id": {
            "type": "string",
            "description": "Unique identifier for the sports facility (e.g., gym ID, stadium code)."
        },
        "equipment_name": {
            "type": "string",
            "description": "Name or type of equipment to check (e.g., treadmill, squat rack, basketball hoop)."
        },
        "last_service_date": {
            "type": "string",
            "description": "Date when equipment was last serviced, in YYYY-MM-DD format.",
            "examples": [
                "2024-11-15"
            ]
        },
        "condition_grade": {
            "type": "string",
            "description": "Assessed condition of the equipment (excellent, good, fair, poor, critical).",
            "enum": [
                "excellent",
                "good",
                "fair",
                "poor",
                "critical"
            ]
        },
        "service_interval_days": {
            "type": "integer",
            "description": "Optional: Number of days between recommended services (default 90).",
            "examples": [
                90,
                180,
                365
            ]
        }
    },
    "required": [
        "facility_id",
        "equipment_name",
        "last_service_date",
        "condition_grade"
    ]
},
}
