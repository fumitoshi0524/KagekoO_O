"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a time-series chart of patient vital signs."""
    import json
    from datetime import datetime, timedelta
    import random
    import math

    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        vital_signs = data.get('vital_signs', [])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        chart_type = data.get('chart_type', 'line')
        show_normal_ranges = data.get('show_normal_ranges', True)

        # Validate required fields
        if not patient_id:
            return json.dumps({'error': 'patient_id is required'}, ensure_ascii=False)
        if not vital_signs:
            return json.dumps({'error': 'vital_signs must contain at least one sign'}, ensure_ascii=False)
        if not start_date or not end_date:
            return json.dumps({'error': 'start_date and end_date are required'}, ensure_ascii=False)

        # Parse dates
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD'}, ensure_ascii=False)

        if end < start:
            return json.dumps({'error': 'end_date must be after start_date'}, ensure_ascii=False)

        # Normal ranges for vital signs
        normal_ranges = {
            'heart_rate': {'min': 60, 'max': 100, 'unit': 'bpm'},
            'blood_pressure_systolic': {'min': 90, 'max': 120, 'unit': 'mmHg'},
            'blood_pressure_diastolic': {'min': 60, 'max': 80, 'unit': 'mmHg'},
            'temperature': {'min': 36.0, 'max': 37.5, 'unit': '°C'},
            'respiratory_rate': {'min': 12, 'max': 20, 'unit': 'breaths/min'},
            'oxygen_saturation': {'min': 95, 'max': 100, 'unit': '%'}
        }

        # Generate simulated vital signs data for demonstration
        # In production, this would query a real patient data system
        days_difference = (end - start).days
        num_measurements = min(days_difference * 4, 100)  # Max 100 data points
        
        time_points = []
        for i in range(num_measurements):
            hours_offset = random.randint(0, 23)
            minutes_offset = random.randint(0, 59)
            measurement_time = start + timedelta(days=i/4) + timedelta(hours=hours_offset, minutes=minutes_offset)
            time_points.append(measurement_time.isoformat())

        # Sort time points chronologically
        time_points.sort()

        # Generate data for each vital sign
        series_data = []
        seed = hash(patient_id) % 10000
        random.seed(seed)

        for sign in vital_signs:
            if sign not in normal_ranges:
                continue
                
            normal = normal_ranges[sign]
            values = []
            
            # Generate trending values with some noise
            base_value = (normal['min'] + normal['max']) / 2
            trend = (random.random() - 0.5) * 0.1  # Slight upward or downward trend
            
            for i, tp in enumerate(time_points):
                noise = (random.random() - 0.5) * (normal['max'] - normal['min']) * 0.3
                trend_component = trend * i
                value = base_value + noise + trend_component
                
                # Ensure values stay in reasonable range
                value = max(normal['min'] - 10, min(normal['max'] + 10, value))
                
                values.append({
                    'time': tp,
                    'value': round(value, 2),
                    'is_out_of_range': value < normal['min'] or value > normal['max']
                })
            
            series_data.append({
                'name': sign.replace('_', ' ').title(),
                'unit': normal['unit'],
                'data': values,
                'normal_range': {
                    'min': normal['min'],
                    'max': normal['max']
                } if show_normal_ranges else None
            })
            
            # Re-seed for next sign to get different patterns
            seed += 1
            random.seed(seed)

        result = {
            'patient_id': patient_id,
            'chart_type': chart_type,
            'title': f'Patient {patient_id} Vital Signs Trends',
            'date_range': {'start': start_date, 'end': end_date},
            'series': series_data,
            'metadata': {
                'total_measurements': len(time_points),
                'vital_signs_count': len(series_data),
                'generated_at': datetime.now().isoformat()
            }
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': f'Failed to process vital signs chart request: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "patient_vitals_chart",
    "description": "Generate a time-series line chart of patient vital signs (heart rate, blood pressure, temperature, respiratory rate, oxygen saturation) over a specified date range, returning chart data suitable for medical dashboard display and clinical trend analysis.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient in the healthcare system"
        },
        "vital_signs": {
            "type": "array",
            "description": "List of vital sign types to include in the chart",
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
            }
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the chart data range in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "End date for the chart data range in YYYY-MM-DD format"
        },
        "chart_type": {
            "type": "string",
            "description": "Optional: Type of chart to generate. Default is line chart.",
            "enum": [
                "line",
                "area",
                "scatter"
            ],
            "default": "line"
        },
        "show_normal_ranges": {
            "type": "boolean",
            "description": "Optional: Whether to overlay normal range indicators on the chart. Default is True.",
            "default": True
        }
    },
    "required": [
        "patient_id",
        "vital_signs",
        "start_date",
        "end_date"
    ]
},
}
