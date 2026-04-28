"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        experiment_id = data.get('experiment_id')
        action = data.get('action')
        sensor_ids = data.get('sensor_ids', None)
        thresholds = data.get('thresholds', {})

        if not experiment_id or not action:
            return json.dumps({'error': 'Missing required parameters: experiment_id and action'}, ensure_ascii=False)

        # Simulated sensor data store (in production would query a real monitoring system)
        simulated_sensors = {
            'sensor_temp_01': {'type': 'temperature', 'value': 22.3, 'unit': 'C', 'status': 'normal'},
            'sensor_hum_02': {'type': 'humidity', 'value': 45.2, 'unit': '%', 'status': 'normal'},
            'sensor_pres_03': {'type': 'pressure', 'value': 1013.1, 'unit': 'hPa', 'status': 'normal'},
            'sensor_light_04': {'type': 'light_intensity', 'value': 320, 'unit': 'lux', 'status': 'normal'}
        }

        if sensor_ids:
            sensors = {k: v for k, v in simulated_sensors.items() if k in sensor_ids}
            if not sensors:
                return json.dumps({'error': 'No valid sensor IDs provided'}, ensure_ascii=False)
        else:
            sensors = simulated_sensors

        if action == 'read':
            result = {
                'experiment_id': experiment_id,
                'timestamp': '2025-04-09T14:30:00Z',
                'sensors': sensors,
                'alarms': []
            }
            # Check thresholds if set (for demo we assume thresholds already configured)
            # In production would load from persistent config
            return json.dumps(result, ensure_ascii=False)

        elif action == 'set_thresholds':
            # Validate thresholds object
            if not thresholds:
                return json.dumps({'error': 'Thresholds required for set_thresholds action'}, ensure_ascii=False)
            # In production, store thresholds in config database
            result = {
                'experiment_id': experiment_id,
                'action': 'set_thresholds',
                'status': 'success',
                'thresholds_applied': thresholds
            }
            return json.dumps(result, ensure_ascii=False)

        elif action == 'calibrate':
            # Simulate calibration: set all sensors to baseline
            for sid in sensors:
                sensors[sid]['status'] = 'calibrating'
            result = {
                'experiment_id': experiment_id,
                'action': 'calibrate',
                'status': 'success',
                'sensors_calibrated': list(sensors.keys()),
                'message': 'Zeroing procedure initiated for all sensors'
            }
            return json.dumps(result, ensure_ascii=False)

        else:
            return json.dumps({'error': f'Unknown action: {action}'}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': f'Failed to process request: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "experiment_environment_monitor",
    "description": "Monitor and configure the environmental conditions of a scientific laboratory experiment (temperature, humidity, pressure, light intensity) and return current readings, status flags, and historical trend indicators for quality assurance.",
    "category": "system",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "experiment_id": {
            "type": "string",
            "description": "Unique identifier for the scientific experiment or laboratory session."
        },
        "sensor_ids": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of sensor identifiers to query (e.g., 'sensor_temp_01', 'sensor_hum_02'). Optional: if omitted, all available sensors for the experiment are returned."
        },
        "action": {
            "type": "string",
            "enum": [
                "read",
                "set_thresholds",
                "calibrate"
            ],
            "description": "Operation to perform: 'read' returns current readings, 'set_thresholds' updates alarm limits, 'calibrate' triggers a sensor zeroing procedure."
        },
        "thresholds": {
            "type": "object",
            "properties": {
                "temperature_min": {
                    "type": "number",
                    "description": "Minimum acceptable temperature in Celsius."
                },
                "temperature_max": {
                    "type": "number",
                    "description": "Maximum acceptable temperature in Celsius."
                },
                "humidity_min": {
                    "type": "number",
                    "description": "Minimum relative humidity in percent."
                },
                "humidity_max": {
                    "type": "number",
                    "description": "Maximum relative humidity in percent."
                }
            },
            "description": "Threshold configuration for alarms. Required only when action is 'set_thresholds'."
        }
    },
    "required": [
        "experiment_id",
        "action"
    ]
},
}
