"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Configure and retrieve travel alert thresholds for system monitoring of transportation disruptions, weather warnings, and security advisories in specified regions."""
    import json
    try:
        data = json.loads(payload)
        region = data.get('region')
        if not region:
            return json.dumps({'error': 'Missing required field: region'}, ensure_ascii=False)
        alert_level = data.get('alert_level')
        notification_channel = data.get('notification_channel', 'dashboard')
        regions = [r.strip().upper() for r in region.split(',')]
        valid_regions = ['JP', 'US', 'EU', 'GB', 'FR', 'DE', 'IT', 'ES', 'CN', 'KR', 'AU', 'CA', 'MX', 'BR', 'IN', 'RU', 'ZA', 'AE', 'SG', 'TH']
        invalid = [r for r in regions if r not in valid_regions]
        if invalid:
            return json.dumps({'error': f'Invalid regions: {invalid}'}, ensure_ascii=False)
        # Simulate stored configuration (in production, use a database or config file)
        stored_config = {
            'JP': {'alert_level': 2, 'notification_channel': 'email'},
            'US': {'alert_level': 3, 'notification_channel': 'dashboard'},
            'EU': {'alert_level': 1, 'notification_channel': 'sms'},
        }
        result = {}
        for r in regions:
            if alert_level is not None:
                # Update threshold
                stored_config[r] = {
                    'alert_level': alert_level,
                    'notification_channel': notification_channel
                }
                result[r] = {'status': 'updated', 'alert_level': alert_level, 'notification_channel': notification_channel}
            else:
                # Retrieve current config
                config = stored_config.get(r, {'alert_level': 1, 'notification_channel': 'dashboard'})
                result[r] = {'alert_level': config['alert_level'], 'notification_channel': config['notification_channel']}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "travel_alert_config",
    "description": "Configure and retrieve travel alert thresholds for system monitoring of transportation disruptions, weather warnings, and security advisories in specified regions, returning the current alert settings or a confirmation of updates.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "region": {
            "type": "string",
            "description": "ISO 3166-1 alpha-2 country code or region name (e.g., 'JP', 'US', 'Europe'). Supports up to 3 comma-separated codes."
        },
        "alert_level": {
            "type": "integer",
            "description": "Threshold alert level (1=informational, 2=advisory, 3=warning, 4=severe). Optional: if provided, sets the threshold; if omitted, returns current config.",
            "minimum": 1,
            "maximum": 4
        },
        "notification_channel": {
            "type": "string",
            "description": "Optional: notification delivery channel (email, sms, dashboard, all).",
            "enum": [
                "email",
                "sms",
                "dashboard",
                "all"
            ]
        }
    },
    "required": [
        "region"
    ]
},
}
