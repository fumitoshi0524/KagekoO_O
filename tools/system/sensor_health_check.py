"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Check the operational status and data quality of environmental monitoring sensors."""
    import json
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        return f'error: Invalid JSON input - {e}'

    # Validate required field
    if 'sensor_ids' not in data:
        return 'error: Missing required parameter "sensor_ids"'

    sensor_ids = data['sensor_ids']
    if not isinstance(sensor_ids, list) or len(sensor_ids) == 0:
        return 'error: "sensor_ids" must be a non-empty array of strings'

    include_raw = data.get('include_raw_metrics', False)
    if not isinstance(include_raw, bool):
        return 'error: "include_raw_metrics" must be a boolean if provided'

    # Simulated sensor state database (real implementation would query an actual API)
    sensor_db = {
        'AQM-001': {'last_ping': datetime.now() - timedelta(hours=2), 'battery': 85, 'calibration': datetime.now() - timedelta(days=30), 'total_data_points': 1000, 'missing_points': 12, 'alerts': []},
        'AQM-002': {'last_ping': datetime.now() - timedelta(days=2), 'battery': 15, 'calibration': datetime.now() - timedelta(days=180), 'total_data_points': 500, 'missing_points': 120, 'alerts': ['low_battery']},
        'WTHR-042': {'last_ping': datetime.now() - timedelta(hours=1), 'battery': 72, 'calibration': datetime.now() - timedelta(days=45), 'total_data_points': 2000, 'missing_points': 5, 'alerts': []},
        'SOIL-009': {'last_ping': datetime.now() - timedelta(days=5), 'battery': 5, 'calibration': datetime.now() - timedelta(days=365), 'total_data_points': 100, 'missing_points': 60, 'alerts': ['low_battery', 'calibration_overdue']}
    }

    result = []
    for sid in sensor_ids:
        if not isinstance(sid, str) or not sid.strip():
            result.append({
                'sensor_id': str(sid),
                'status': 'invalid',
                'message': 'Sensor ID must be a non-empty string'
            })
            continue

        sid = sid.strip()
        if sid not in sensor_db:
            result.append({
                'sensor_id': sid,
                'status': 'unknown',
                'message': 'Sensor not found in registry'
            })
            continue

        info = sensor_db[sid]
        now = datetime.now()

        # Compute metrics
        hours_since_ping = (now - info['last_ping']).total_seconds() / 3600
        online = hours_since_ping < 24
        days_since_calibration = (now - info['calibration']).days
        data_completeness = round((info['total_data_points'] - info['missing_points']) / info['total_data_points'] * 100, 1) if info['total_data_points'] > 0 else 0.0
        anomalies = info['alerts']

        entry = {
            'sensor_id': sid,
            'online_status': 'online' if online else 'offline',
            'last_contact_utc': info['last_ping'].strftime('%Y-%m-%d %H:%M:%S'),
            'days_since_calibration': days_since_calibration,
            'calibration_overdue': days_since_calibration > 365,
            'data_completeness_percent': data_completeness,
            'anomalies': anomalies
        }

        if include_raw:
            entry['battery_level_percent'] = info['battery']
            entry['last_transmission_utc'] = info['last_ping'].strftime('%Y-%m-%d %H:%M:%S')

        result.append(entry)

    return json.dumps({'checked_sensors': result, 'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sensor_health_check",
    "description": "Check the operational status and data quality of environmental monitoring sensors (air quality monitors, weather stations, water level gauges, soil moisture probes) and return a structured report including online status, last calibration date, data completeness ratio, and anomaly flags.",
    "category": "system",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "sensor_ids": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of sensor identifiers to check. Each ID must be a valid alphanumeric string (e.g., 'AQM-001', 'WTHR-042')."
        },
        "include_raw_metrics": {
            "type": "boolean",
            "description": "Optional: If True, includes raw battery level and last transmission timestamp in the output. Default is False."
        }
    },
    "required": [
        "sensor_ids"
    ]
},
}
