"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import random
    import math

    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        vital_sign_types = data.get('vital_sign_types', ['heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'temperature', 'respiratory_rate', 'oxygen_saturation'])
        aggregation = data.get('aggregation', 'raw')

        if not patient_id or not start_date_str or not end_date_str:
            return json.dumps({'error': 'Missing required fields: patient_id, start_date, end_date'}, ensure_ascii=False)

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        if start_date > end_date:
            return json.dumps({'error': 'start_date must be before or equal to end_date'}, ensure_ascii=False)

        valid_types = ['heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'temperature', 'respiratory_rate', 'oxygen_saturation']
        for vt in vital_sign_types:
            if vt not in valid_types:
                return json.dumps({'error': f'Invalid vital_sign_type: {vt}'}, ensure_ascii=False)

        # Simulate generating vital signs data based on patient_id as seed
        random.seed(hash(patient_id) % (2**31) + int(start_date.timestamp()))
        
        timeline_data = {}
        for vt in vital_sign_types:
            timeline_data[vt] = []

        # Determine the number of data points based on date range and aggregation
        total_days = (end_date - start_date).days
        
        if aggregation == 'raw':
            # Simulate 3-8 measurements per day
            current_date = start_date
            while current_date <= end_date:
                num_measurements = random.randint(3, 8)
                for _ in range(num_measurements):
                    hours = random.randint(0, 23)
                    minutes = random.randint(0, 59)
                    timestamp = current_date.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                    for vt in vital_sign_types:
                        if vt == 'heart_rate':
                            value = round(random.gauss(75, 10), 0)
                        elif vt == 'blood_pressure_systolic':
                            value = round(random.gauss(120, 12), 0)
                        elif vt == 'blood_pressure_diastolic':
                            value = round(random.gauss(80, 8), 0)
                        elif vt == 'temperature':
                            value = round(random.gauss(37.0, 0.3), 1)
                        elif vt == 'respiratory_rate':
                            value = round(random.gauss(16, 3), 0)
                        elif vt == 'oxygen_saturation':
                            value = round(random.gauss(98, 1.5), 0)
                        timeline_data[vt].append({
                            'timestamp': timestamp.isoformat(),
                            'value': value
                        })
                current_date += timedelta(days=1)
        elif aggregation in ['hourly', 'daily', 'weekly']:
            current_date = start_date
            while current_date <= end_date:
                if aggregation == 'hourly':
                    for hour in range(0, 24):
                        timestamp = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                        for vt in vital_sign_types:
                            if vt == 'heart_rate':
                                value = round(random.gauss(75, 5), 0)
                            elif vt == 'blood_pressure_systolic':
                                value = round(random.gauss(120, 8), 0)
                            elif vt == 'blood_pressure_diastolic':
                                value = round(random.gauss(80, 5), 0)
                            elif vt == 'temperature':
                                value = round(random.gauss(37.0, 0.2), 1)
                            elif vt == 'respiratory_rate':
                                value = round(random.gauss(16, 2), 0)
                            elif vt == 'oxygen_saturation':
                                value = round(random.gauss(98, 1), 0)
                            timeline_data[vt].append({
                                'timestamp': timestamp.isoformat(),
                                'value': value
                            })
                elif aggregation == 'daily':
                    timestamp = current_date.replace(hour=12, minute=0, second=0, microsecond=0)
                    for vt in vital_sign_types:
                        if vt == 'heart_rate':
                            avg = random.gauss(75, 3)
                        elif vt == 'blood_pressure_systolic':
                            avg = random.gauss(120, 5)
                        elif vt == 'blood_pressure_diastolic':
                            avg = random.gauss(80, 3)
                        elif vt == 'temperature':
                            avg = random.gauss(37.0, 0.1)
                        elif vt == 'respiratory_rate':
                            avg = random.gauss(16, 1)
                        elif vt == 'oxygen_saturation':
                            avg = random.gauss(98, 0.5)
                        timeline_data[vt].append({
                            'timestamp': timestamp.isoformat(),
                            'value': round(avg, 1) if vt == 'temperature' else round(avg, 0)
                        })
                elif aggregation == 'weekly':
                    current_week_start = current_date - timedelta(days=current_date.weekday())
                    timestamp = current_week_start.replace(hour=12, minute=0, second=0, microsecond=0)
                    for vt in vital_sign_types:
                        if vt == 'heart_rate':
                            avg = random.gauss(75, 2)
                        elif vt == 'blood_pressure_systolic':
                            avg = random.gauss(120, 3)
                        elif vt == 'blood_pressure_diastolic':
                            avg = random.gauss(80, 2)
                        elif vt == 'temperature':
                            avg = random.gauss(37.0, 0.05)
                        elif vt == 'respiratory_rate':
                            avg = random.gauss(16, 0.5)
                        elif vt == 'oxygen_saturation':
                            avg = random.gauss(98, 0.3)
                        timeline_data[vt].append({
                            'timestamp': timestamp.isoformat(),
                            'value': round(avg, 1) if vt == 'temperature' else round(avg, 0)
                        })
                    current_date += timedelta(days=7)
                    continue
                current_date += timedelta(days=1 if aggregation in ['hourly', 'daily'] else 0)

        result = {
            'patient_id': patient_id,
            'date_range': {'start': start_date_str, 'end': end_date_str},
            'aggregation': aggregation,
            'total_data_points': sum(len(v) for v in timeline_data.values()),
            'vital_signs_timeline': timeline_data
        }

        return json.dumps(result, ensure_ascii=False, default=str)
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "patient_vital_signs_timeline",
    "description": "Generate a chronological timeline visualization of a patient's vital signs measurements (heart rate, blood pressure, temperature, respiratory rate) over a specified date range, returning structured data suitable for rendering line charts that help clinicians track health trends and detect anomalies.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient whose vital signs are to be retrieved",
            "examples": [
                "P-12345",
                "PT-9876"
            ]
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the timeline in ISO 8601 format (YYYY-MM-DD)",
            "examples": [
                "2024-01-01"
            ]
        },
        "end_date": {
            "type": "string",
            "description": "End date for the timeline in ISO 8601 format (YYYY-MM-DD)",
            "examples": [
                "2024-12-31"
            ]
        },
        "vital_sign_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "heart_rate",
                    "blood_pressure_systolic",
                    "blood_pressure_diastolic",
                    "temperature",
                    "respiratory_rate",
                    "oxygen_saturation"
                ]
            },
            "description": "Optional: List of vital sign types to include; default is all available types",
            "examples": [
                [
                    "heart_rate",
                    "temperature",
                    "respiratory_rate"
                ]
            ]
        },
        "aggregation": {
            "type": "string",
            "enum": [
                "raw",
                "hourly",
                "daily",
                "weekly"
            ],
            "description": "Optional: Aggregation interval for the data points; default is 'raw' for all recorded measurements",
            "examples": [
                "daily"
            ]
        }
    },
    "required": [
        "patient_id",
        "start_date",
        "end_date"
    ]
},
}
