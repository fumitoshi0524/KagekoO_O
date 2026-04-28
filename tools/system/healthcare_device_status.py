"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Monitor the operational status of registered medical devices by device ID, returning current connectivity state, battery level (if applicable), last calibration date, and any active error codes, used for proactive maintenance alerts."""
    import json
    from datetime import datetime, timedelta
    import random
    try:
        data = json.loads(payload)
        device_id = data.get('device_id')
        if not device_id or not isinstance(device_id, str) or len(device_id.strip()) == 0:
            raise ValueError('Device ID is required and must be a non-empty string')
        
        # Simulate querying device registry and telemetry
        # In production, this would query an IoT hub or device management database
        device_prefix = device_id.split('-')[0].upper() if '-' in device_id else device_id[:4].upper()
        
        # Generate realistic status data
        connectivity_states = ['online', 'offline', 'degraded']
        connectivity = random.choices(connectivity_states, weights=[0.85, 0.08, 0.07])[0]
        
        battery_level = None
        if device_prefix in ['PUMP', 'ECG', 'OXI', 'BP']:
            battery_level = round(random.uniform(20.0, 100.0), 1)
        
        # Last calibration within the last 90 days
        days_since_cal = random.randint(0, 90)
        last_calibration = (datetime.now() - timedelta(days=days_since_cal)).isoformat()
        
        # Error codes
        possible_errors = ['ERR-01: Sensor failure', 'ERR-07: Communication timeout', 
                          'ERR-23: Low battery', 'ERR-99: Calibration overdue', 
                          'ERR-12: Temperature out of range']
        active_errors = []
        if connectivity == 'degraded':
            active_errors.append(random.choice(possible_errors))
        if battery_level and battery_level < 30:
            active_errors.append('ERR-23: Low battery')
        if days_since_cal > 60:
            active_errors.append('ERR-99: Calibration overdue')
        
        result = {
            'device_id': device_id,
            'connectivity': connectivity,
            'battery_level_percent': battery_level,
            'last_calibration': last_calibration,
            'active_errors': active_errors if active_errors else 'none',
            'checked_at': datetime.now().isoformat()
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "healthcare_device_status",
    "description": "Monitor the operational status of registered medical devices by device ID, returning current connectivity state, battery level (if applicable), last calibration date, and any active error codes, used for proactive maintenance alerts.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "device_id": {
            "type": "string",
            "description": "Unique identifier for the medical device (e.g., infusion pump serial number or asset tag)",
            "examples": [
                "PUMP-12345",
                "MRI-X900-001"
            ]
        }
    },
    "required": [
        "device_id"
    ]
},
}
