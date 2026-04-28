"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        op = data.get('operation')
        destination = data.get('destination')
        alert_type = data.get('alert_type')
        severity = data.get('severity')
        message = data.get('message')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        alert_id = data.get('alert_id')

        if not all([op, destination, alert_type, severity, message, start_date]):
            return json.dumps({'error': 'Missing required fields'})
        
        # Validate date format
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid start_date format, expected YYYY-MM-DD'})
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'Invalid end_date format, expected YYYY-MM-DD'})
        else:
            # Default to 7 days from start
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = (start + timedelta(days=7)).strftime('%Y-%m-%d')

        # In a real system, this would interact with a database or API
        # Simulate alert management
        alerts = []
        if op == 'create':
            new_alert = {
                'alert_id': alert_id or f'ALERT-{datetime.now().timestamp()}',
                'destination': destination,
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                'start_date': start_date,
                'end_date': end_date,
                'status': 'active'
            }
            alerts.append(new_alert)
            result = {'message': 'Alert created successfully', 'alerts': alerts}
        elif op == 'update':
            if not alert_id:
                return json.dumps({'error': 'alert_id required for update'})
            updated_alert = {
                'alert_id': alert_id,
                'destination': destination,
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                'start_date': start_date,
                'end_date': end_date,
                'status': 'updated'
            }
            alerts.append(updated_alert)
            result = {'message': f'Alert {alert_id} updated', 'alerts': alerts}
        elif op == 'cancel':
            if not alert_id:
                return json.dumps({'error': 'alert_id required for cancel'})
            cancelled_alert = {
                'alert_id': alert_id,
                'destination': destination,
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                'start_date': start_date,
                'end_date': end_date,
                'status': 'cancelled'
            }
            alerts.append(cancelled_alert)
            result = {'message': f'Alert {alert_id} cancelled', 'alerts': alerts}
        else:
            return json.dumps({'error': 'Invalid operation'})

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "travel_alert_manager",
    "description": "Manage travel alerts for destinations: create, update, or cancel travel advisories (e.g., weather, security, health) for specific cities or regions, returning a list of active alerts with severity, type, and effective date range.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": [
                "create",
                "update",
                "cancel"
            ],
            "description": "Operation to perform on the alert"
        },
        "destination": {
            "type": "string",
            "description": "City or region name for the travel alert, e.g., 'Paris' or 'Bali'"
        },
        "alert_type": {
            "type": "string",
            "enum": [
                "weather",
                "security",
                "health",
                "transport",
                "other"
            ],
            "description": "Category of the travel alert"
        },
        "severity": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high",
                "critical"
            ],
            "description": "Severity level of the alert"
        },
        "message": {
            "type": "string",
            "description": "Descriptive text for the alert"
        },
        "start_date": {
            "type": "string",
            "description": "Start date of alert validity in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "Optional: End date of alert validity in YYYY-MM-DD format (default 7 days from start)"
        },
        "alert_id": {
            "type": "string",
            "description": "Optional: Alert identifier for update or cancel operations"
        }
    },
    "required": [
        "operation",
        "destination",
        "alert_type",
        "severity",
        "message",
        "start_date"
    ]
},
}
