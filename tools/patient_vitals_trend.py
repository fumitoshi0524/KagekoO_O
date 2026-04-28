"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a time-series trend visualization of patient vital signs."""
    import json
    from datetime import datetime, timedelta
    import random
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        vital_sign = data.get('vital_sign')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        include_thresholds = data.get('include_alert_thresholds', True)

        if not all([patient_id, vital_sign, start_date, end_date]):
            return json.dumps({'error': 'Missing required parameters: patient_id, vital_sign, start_date, end_date'})

        # Validate dates
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD.'})

        if end_dt < start_dt:
            return json.dumps({'error': 'end_date must be after start_date'})

        # Simulate vital sign data generation (would query a real database in production)
        vital_units = {
            'heart_rate': 'bpm',
            'systolic_bp': 'mmHg',
            'diastolic_bp': 'mmHg',
            'temperature': '°C',
            'oxygen_saturation': '%'
        }

        normal_ranges = {
            'heart_rate': (60, 100),
            'systolic_bp': (90, 120),
            'diastolic_bp': (60, 80),
            'temperature': (36.1, 37.2),
            'oxygen_saturation': (95, 100)
        }

        # Generate daily data points
        trend_data = []
        current_date = start_dt
        base_value = random.uniform(70, 85) if vital_sign == 'heart_rate' else random.uniform(100, 130) if vital_sign in ['systolic_bp', 'diastolic_bp'] else random.uniform(36.5, 37.0) if vital_sign == 'temperature' else random.uniform(96, 99)

        while current_date <= end_dt:
            # Simulate daily variation
            variation = random.uniform(-5, 5)
            if vital_sign == 'temperature':
                variation = random.uniform(-0.3, 0.3)
            value = round(base_value + variation, 1)

            # Ensure values stay within plausible ranges
            if vital_sign == 'heart_rate':
                value = max(40, min(200, value))
            elif vital_sign in ['systolic_bp', 'diastolic_bp']:
                value = max(50, min(250, value))
            elif vital_sign == 'temperature':
                value = max(35.0, min(42.0, value))
            elif vital_sign == 'oxygen_saturation':
                value = max(85, min(100, round(value, 0)))

            trend_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': value,
                'unit': vital_units.get(vital_sign, ''),
                'alert': value < normal_ranges.get(vital_sign, (0, 0))[0] or value > normal_ranges.get(vital_sign, (0, 0))[1]
            })
            current_date += timedelta(days=1)

        result = {
            'patient_id': patient_id,
            'vital_sign': vital_sign,
            'unit': vital_units.get(vital_sign, ''),
            'start_date': start_date,
            'end_date': end_date,
            'data_points': trend_data
        }

        # Add alert thresholds if requested
        if include_thresholds:
            normal = normal_ranges.get(vital_sign, (None, None))
            result['alert_lower_threshold'] = normal[0]
            result['alert_upper_threshold'] = normal[1]

        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Failed to generate vital sign trend: {str(e)}'})


TOOL_SPEC = {
    "name": "patient_vitals_trend",
    "description": "Generate a time-series trend visualization of patient vital signs (heart rate, blood pressure, temperature, oxygen saturation) over a specified date range, returning structured data suitable for chart rendering.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., medical record number, UUID)"
        },
        "vital_sign": {
            "type": "string",
            "enum": [
                "heart_rate",
                "systolic_bp",
                "diastolic_bp",
                "temperature",
                "oxygen_saturation"
            ],
            "description": "Type of vital sign to visualize"
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the trend period in ISO 8601 format (YYYY-MM-DD)"
        },
        "end_date": {
            "type": "string",
            "description": "End date for the trend period in ISO 8601 format (YYYY-MM-DD)"
        },
        "include_alert_thresholds": {
            "type": "boolean",
            "description": "Optional: Include clinical alert thresholds (normal range lines) in the output data. Default is true.",
            "default": true
        }
    },
    "required": [
        "patient_id",
        "vital_sign",
        "start_date",
        "end_date"
    ]
},
}
