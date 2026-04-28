"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Calculate upcoming subscription expiry dates for recurring services."""
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        service_name = data['service_name']
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        billing_cycle = data['billing_cycle']
        threshold = data.get('remaining_days_threshold', 7)
        
        today = datetime.now().date()
        
        if billing_cycle == 'monthly':
            # Calculate next expiry: add one month (simple: 30 days)
            if start_date.month == 12:
                next_expiry = start_date.replace(year=start_date.year+1, month=1)
            else:
                next_expiry = start_date.replace(month=start_date.month+1)
        elif billing_cycle == 'quarterly':
            next_expiry = start_date + timedelta(days=90)
        elif billing_cycle == 'yearly':
            next_expiry = start_date.replace(year=start_date.year+1)
        else:
            return json.dumps({'error': 'Invalid billing_cycle'}, ensure_ascii=False)
        
        remaining_days = (next_expiry - today).days
        
        alert = 'Critical - expires today!' if remaining_days <= 0 else \
                f'Expires in {remaining_days} day(s).' if remaining_days > 0 else ''
        
        if remaining_days <= threshold and remaining_days > 0:
            alert = f'Warning: {service_name} expires in {remaining_days} day(s). Consider renewal soon.'
        
        result = {
            'service_name': service_name,
            'expiry_date': next_expiry.isoformat(),
            'remaining_days': remaining_days,
            'alert_message': alert
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "subscription_expiry_alert",
    "description": "Calculate upcoming subscription expiry dates for recurring services (e.g., streaming, gym, software) and generate a human-readable alert with remaining days and recommended action.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "service_name": {
            "type": "string",
            "description": "Name of the subscription service (e.g., Netflix, Spotify, gym membership)."
        },
        "start_date": {
            "type": "string",
            "format": "date",
            "description": "Start date of the current billing period in YYYY-MM-DD format."
        },
        "billing_cycle": {
            "type": "string",
            "enum": [
                "monthly",
                "quarterly",
                "yearly"
            ],
            "description": "Frequency of billing: monthly, quarterly, or yearly."
        },
        "remaining_days_threshold": {
            "type": "integer",
            "description": "Optional: Number of days before expiry to trigger a warning (default 7).",
            "minimum": 0
        }
    },
    "required": [
        "service_name",
        "start_date",
        "billing_cycle"
    ]
},
}
