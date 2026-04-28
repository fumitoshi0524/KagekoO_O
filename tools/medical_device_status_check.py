"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        device_id = data.get('device_id')
        device_type = data.get('device_type')
        include_history = data.get('include_calibration_history', False)

        if not device_id or not device_type:
            return json.dumps({'status': 'error', 'message': 'device_id and device_type are required'})

        # Simulate checking a medical device status database
        device_registry = {
            'infusion_pump': {
                'model': 'Alaris 8015',
                'status': 'operational',
                'calibration_valid': True,
                'last_calibration': '2024-12-15',
                'next_maintenance': '2025-06-15',
                'days_until_maintenance': 60,
                'calibration_history': [
                    {'date': '2024-12-15', 'result': 'passed'},
                    {'date': '2024-06-15', 'result': 'passed'}
                ]
            },
            'ventilator': {
                'model': 'Hamilton G5',
                'status': 'operational',
                'calibration_valid': True,
                'last_calibration': '2025-01-10',
                'next_maintenance': '2025-07-10',
                'days_until_maintenance': 45,
                'calibration_history': [
                    {'date': '2025-01-10', 'result': 'passed'},
                    {'date': '2024-07-10', 'result': 'passed'}
                ]
            },
            'mri_scanner': {
                'model': 'Siemens Magnetom Vida 3T',
                'status': 'operational',
                'calibration_valid': True,
                'last_calibration': '2025-02-01',
                'next_maintenance': '2025-08-01',
                'days_until_maintenance': 70,
                'calibration_history': [
                    {'date': '2025-02-01', 'result': 'passed'},
                    {'date': '2024-08-01', 'result': 'passed'}
                ]
            },
            'defibrillator': {
                'model': 'Philips HeartStart XL+',
                'status': 'needs_battery_replacement',
                'calibration_valid': False,
                'last_calibration': '2024-09-20',
                'next_maintenance': '2025-03-20',
                'days_until_maintenance': -15,
                'calibration_history': [
                    {'date': '2024-09-20', 'result': 'failed'}
                ]
            },
            'patient_monitor': {
                'model': 'GE B40',
                'status': 'operational',
                'calibration_valid': True,
                'last_calibration': '2025-01-25',
                'next_maintenance': '2025-07-25',
                'days_until_maintenance': 55,
                'calibration_history': [
                    {'date': '2025-01-25', 'result': 'passed'},
                    {'date': '2024-07-25', 'result': 'passed'}
                ]
            },
            'ultrasound': {
                'model': 'GE LOGIQ E10',
                'status': 'operational',
                'calibration_valid': True,
                'last_calibration': '2025-02-10',
                'next_maintenance': '2025-08-10',
                'days_until_maintenance': 65,
                'calibration_history': [
                    {'date': '2025-02-10', 'result': 'passed'},
                    {'date': '2024-08-10', 'result': 'passed'}
                ]
            }
        }

        if device_type not in device_registry:
            return json.dumps({'status': 'error', 'message': f'Unknown device_type: {device_type}'})

        device_info = device_registry[device_type]
        result = {
            'device_id': device_id,
            'device_type': device_type,
            'model': device_info['model'],
            'status': device_info['status'],
            'calibration_valid': device_info['calibration_valid'],
            'last_calibration': device_info['last_calibration'],
            'next_maintenance': device_info['next_maintenance'],
            'days_until_maintenance': device_info['days_until_maintenance'],
            'operational_ready': device_info['status'] == 'operational' and device_info['calibration_valid']
        }

        if include_history:
            result['calibration_history'] = device_info['calibration_history']

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "medical_device_status_check",
    "description": "Check the operational status, calibration validity, and maintenance schedule for medical devices such as infusion pumps, ventilators, MRI scanners, and defibrillators, returning a status summary for healthcare inventory management.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "device_id": {
            "type": "string",
            "description": "Unique identifier for the medical device (alphanumeric code assigned during registration)"
        },
        "device_type": {
            "type": "string",
            "enum": [
                "infusion_pump",
                "ventilator",
                "mri_scanner",
                "defibrillator",
                "patient_monitor",
                "ultrasound"
            ],
            "description": "Type of medical device to check"
        },
        "include_calibration_history": {
            "type": "boolean",
            "description": "Optional: Whether to include past calibration records in the response (default false)"
        }
    },
    "required": [
        "device_id",
        "device_type"
    ]
},
}
