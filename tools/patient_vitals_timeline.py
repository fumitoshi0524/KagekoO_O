"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if not patient_id or not start_date or not end_date:
            return json.dumps({'error': 'Missing required parameters: patient_id, start_date, end_date'})
        vital_signs = data.get('vital_signs', ['heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'temperature', 'oxygen_saturation'])
        interval = data.get('interval', 'hourly')
        
        # Simulate fetching vitals data (in production, query a real database)
        # Real logic would retrieve measurements from a medical records system
        import random
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        days_diff = (end_dt - start_dt).days
        time_points = []
        current = start_dt
        while current <= end_dt:
            time_points.append(current.isoformat())
            if interval == 'hourly':
                current += timedelta(hours=1)
            elif interval == 'daily':
                current += timedelta(days=1)
            else:
                current += timedelta(hours=12)
        
        chart_data = []
        for vs in vital_signs:
            series = []
            for t in time_points:
                if vs == 'heart_rate':
                    value = round(random.gauss(75, 10))
                    if value < 40: value = 40
                    if value > 120: value = 120
                elif vs == 'blood_pressure_systolic':
                    value = round(random.gauss(120, 15))
                    if value < 80: value = 80
                    if value > 200: value = 200
                elif vs == 'blood_pressure_diastolic':
                    value = round(random.gauss(80, 10))
                    if value < 50: value = 50
                    if value > 130: value = 130
                elif vs == 'temperature':
                    value = round(random.gauss(37.0, 0.5), 1)
                    if value < 35.0: value = 35.0
                    if value > 40.0: value = 40.0
                elif vs == 'oxygen_saturation':
                    value = round(random.gauss(97, 2))
                    if value < 85: value = 85
                    if value > 100: value = 100
                series.append({'timestamp': t, 'value': value})
            chart_data.append({'vital_sign': vs, 'series': series})
        
        summary = {}
        for vs in vital_signs:
            values = [point['value'] for point in next(item['series'] for item in chart_data if item['vital_sign'] == vs)]
            summary[vs] = {
                'min': min(values),
                'max': max(values),
                'avg': round(sum(values)/len(values), 1)
            }
        
        result = {
            'patient_id': patient_id,
            'interval': interval,
            'chart_data': chart_data,
            'summary_statistics': summary
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'An error occurred: {str(e)}'})


TOOL_SPEC = {
    "name": "patient_vitals_timeline",
    "description": "Generate a visual timeline chart of patient vital signs (heart rate, blood pressure, temperature, oxygen saturation) over a specified date range, returning chart data and summary statistics for clinical review.",
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
            "description": "Start date for the vital signs data range in YYYY-MM-DD format."
        },
        "end_date": {
            "type": "string",
            "description": "End date for the vital signs data range in YYYY-MM-DD format."
        },
        "vital_signs": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "heart_rate",
                    "blood_pressure_systolic",
                    "blood_pressure_diastolic",
                    "temperature",
                    "oxygen_saturation"
                ]
            },
            "description": "List of vital sign types to include in the timeline. Optional: defaults to all if not provided."
        },
        "interval": {
            "type": "string",
            "enum": [
                "hourly",
                "daily",
                "shift"
            ],
            "description": "Optional: Aggregation interval for the data. Defaults to 'hourly'."
        }
    },
    "required": [
        "patient_id",
        "start_date",
        "end_date"
    ]
},
}
