"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        time_range_days = data.get('time_range_days')
        vital_signs = data.get('vital_signs')
        chart_title = data.get('chart_title', 'Patient Vital Trends')
        
        if not patient_id or not time_range_days or not vital_signs:
            return json.dumps({'error': 'Missing required parameters'})
        
        if time_range_days < 1 or time_range_days > 90:
            return json.dumps({'error': 'time_range_days must be between 1 and 90'})
        
        if not isinstance(vital_signs, list) or len(vital_signs) == 0:
            return json.dumps({'error': 'vital_signs must be a non-empty array'})
        
        valid_vitals = {'heart_rate', 'systolic_bp', 'diastolic_bp', 'oxygen_saturation', 'temperature'}
        for vs in vital_signs:
            if vs not in valid_vitals:
                return json.dumps({'error': f'Invalid vital sign: {vs}'})
        
        # Simulate generating chart data based on vital signs timeline
        import random
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=time_range_days)
        
        data_points = []
        current_time = start_time
        while current_time <= end_time:
            point = {'timestamp': current_time.isoformat() + 'Z'}
            for vs in vital_signs:
                if vs == 'heart_rate':
                    point[vs] = random.randint(60, 100)
                elif vs == 'systolic_bp':
                    point[vs] = random.randint(110, 140)
                elif vs == 'diastolic_bp':
                    point[vs] = random.randint(70, 90)
                elif vs == 'oxygen_saturation':
                    point[vs] = round(random.uniform(92.0, 99.0), 1)
                elif vs == 'temperature':
                    point[vs] = round(random.uniform(36.5, 37.5), 1)
            data_points.append(point)
            current_time += timedelta(hours=6)  # Every 6 hours
        
        # Generate HTML chart using plotly-like structure
        import html
        
        chart_data = []
        for vs in vital_signs:
            vs_name = vs.replace('_', ' ').title()
            vs_data = []
            for dp in data_points:
                vs_data.append({'timestamp': dp['timestamp'], 'value': dp[vs]})
            chart_data.append({'name': vs_name, 'data': vs_data})
        
        # Escape for JSON embedding
        chart_json = json.dumps(chart_data)
        
        result = {
            'chart_html': f'<div class="vital-chart"><h3>{html.escape(chart_title)}</h3><p>Patient ID: {html.escape(patient_id)}</p><div id="vital-chart-container" data-chart=\'{chart_json}\'></div></div>',
            'data_points_count': len(data_points),
            'chart_title': chart_title,
            'patient_id': patient_id,
            'time_range_days': time_range_days,
            'vital_signs': vital_signs,
            'generated_at': end_time.isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "patient_vital_trend_visualizer",
    "description": "Generates a line chart visualization of a patient's vital signs (heart rate, blood pressure, oxygen saturation, temperature) over a specified time period, returning an HTML chart for clinical review and trend analysis.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., medical record number)",
            "examples": [
                "P12345",
                "MRN-78901"
            ]
        },
        "time_range_days": {
            "type": "integer",
            "description": "Number of days of historical data to include in the visualization (1 to 90)",
            "minimum": 1,
            "maximum": 90,
            "examples": [
                7,
                14,
                30
            ]
        },
        "vital_signs": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "heart_rate",
                    "systolic_bp",
                    "diastolic_bp",
                    "oxygen_saturation",
                    "temperature"
                ]
            },
            "description": "List of vital signs to include in the chart. At least one must be selected.",
            "minItems": 1,
            "examples": [
                [
                    "heart_rate",
                    "oxygen_saturation"
                ]
            ]
        },
        "chart_title": {
            "type": "string",
            "description": "Optional: Custom title for the chart. Defaults to 'Patient Vital Trends' if not provided.",
            "maxLength": 100,
            "examples": [
                "Post-operative Recovery Trends"
            ]
        }
    },
    "required": [
        "patient_id",
        "time_range_days",
        "vital_signs"
    ]
},
}
