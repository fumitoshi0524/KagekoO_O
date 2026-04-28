"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        vitals_filter = data.get('vitals', None)
        granularity = data.get('granularity', 'daily')
        
        if not patient_id or not start_date_str or not end_date_str:
            return json.dumps({'error': 'Missing required inputs: patient_id, start_date, end_date'})
        
        try:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
        except ValueError:
            return json.dumps({'error': 'Invalid date format, use ISO 8601 (YYYY-MM-DD)'})
        
        if start_date > end_date:
            return json.dumps({'error': 'start_date must be before end_date'})
        
        # Simulate retrieval of vitals data (in production, this queries a health record database)
        # For demonstration, we generate realistic synthetic data
        import random
        random.seed(hash(patient_id) + hash(start_date_str))
        
        all_vitals_types = ['heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'temperature', 'spo2', 'respiratory_rate']
        
        if vitals_filter:
            valid_vitals = [v for v in vitals_filter if v in all_vitals_types]
            if not valid_vitals:
                return json.dumps({'error': 'No valid vital sign types provided. Valid options: ' + ', '.join(all_vitals_types)})
        else:
            valid_vitals = all_vitals_types.copy()
        
        # Determine time steps based on granularity
        time_steps = []
        current = start_date
        while current <= end_date:
            time_steps.append(current.isoformat())
            if granularity == 'daily':
                current += timedelta(days=1)
            elif granularity == 'weekly':
                current += timedelta(weeks=1)
            else:  # hourly
                current += timedelta(hours=1)
        
        timelines = []
        for vital_type in valid_vitals:
            points = []
            for ts in time_steps:
                # Generate realistic vital sign values with some trend and noise
                if vital_type == 'heart_rate':
                    base = 70
                    noise = random.gauss(0, 8)
                    value = round(base + noise, 0)
                elif vital_type == 'blood_pressure_systolic':
                    base = 120
                    noise = random.gauss(0, 10)
                    value = round(base + noise, 0)
                elif vital_type == 'blood_pressure_diastolic':
                    base = 80
                    noise = random.gauss(0, 6)
                    value = round(base + noise, 0)
                elif vital_type == 'temperature':
                    base = 36.6
                    noise = random.gauss(0, 0.2)
                    value = round(base + noise, 1)
                elif vital_type == 'spo2':
                    base = 97
                    noise = random.gauss(0, 1)
                    value = max(90, min(100, round(base + noise, 0)))
                elif vital_type == 'respiratory_rate':
                    base = 16
                    noise = random.gauss(0, 3)
                    value = max(8, round(base + noise, 0))
                
                points.append({'timestamp': ts, 'value': value})
            
            timelines.append({
                'vital_type': vital_type,
                'unit': {
                    'heart_rate': 'bpm',
                    'blood_pressure_systolic': 'mmHg',
                    'blood_pressure_diastolic': 'mmHg',
                    'temperature': '°C',
                    'spo2': '%',
                    'respiratory_rate': 'breaths/min'
                }.get(vital_type, ''),
                'data_points': points
            })
        
        result = {
            'patient_id': patient_id,
            'date_range': {'start': start_date_str, 'end': end_date_str},
            'granularity': granularity,
            'timelines': timelines,
            'total_data_points': sum(len(t['data_points']) for t in timelines)
        }
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Internal error: {str(e)}'})


TOOL_SPEC = {
    "name": "health_vitals_timeline",
    "description": "Generates a chronological timeline visualization of a patient's vital signs over a specified date range, returning structured data suitable for chart rendering that illustrates trends in metrics such as heart rate, blood pressure, temperature, and SpO2.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., medical record number)."
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the timeline in ISO 8601 format (e.g., YYYY-MM-DD)."
        },
        "end_date": {
            "type": "string",
            "description": "End date for the timeline in ISO 8601 format (e.g., YYYY-MM-DD)."
        },
        "vitals": {
            "type": "array",
            "description": "Optional: List of vital sign types to include. If omitted, all available vital types are returned.",
            "items": {
                "type": "string",
                "enum": [
                    "heart_rate",
                    "blood_pressure_systolic",
                    "blood_pressure_diastolic",
                    "temperature",
                    "spo2",
                    "respiratory_rate"
                ]
            }
        },
        "granularity": {
            "type": "string",
            "description": "Optional: Aggregation interval for data points. Defaults to 'daily'.",
            "enum": [
                "hourly",
                "daily",
                "weekly"
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
