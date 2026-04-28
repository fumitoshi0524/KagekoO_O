"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import random
    import statistics
    
    try:
        data = json.loads(payload)
        patient_id = data['patient_id']
        metric = data['metric']
        interval = data['interval']
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        aggregation = data.get('aggregation', 'average')
        
        if end_date < start_date:
            return json.dumps({'error': 'end_date must be after or equal to start_date'})
        
        # Simulate time-series data (replace with real DB queries in production)
        # Generate realistic patterns per metric type
        base_ranges = {
            'heart_rate': (60, 100),
            'blood_pressure_systolic': (110, 130),
            'blood_pressure_diastolic': (70, 90),
            'temperature': (36.0, 37.5),
            'oxygen_saturation': (95, 100),
            'respiratory_rate': (12, 20)
        }
        base_low, base_high = base_ranges.get(metric, (0, 1))
        
        # Generate datetime points between start and end dates
        current = start_date
        timestamps = []
        while current <= end_date:
            if interval == 'hourly':
                for h in range(24):
                    timestamps.append(current.replace(hour=h, minute=0, second=0, microsecond=0))
            elif interval == 'daily':
                timestamps.append(current.replace(hour=12, minute=0, second=0, microsecond=0))
            elif interval == 'weekly':
                if current.weekday() == 0:  # Monday
                    timestamps.append(current.replace(hour=12, minute=0, second=0, microsecond=0))
            current += timedelta(days=1)
        
        # For each timestamp, generate aggregated value based on simulated raw readings
        series = []
        for ts in timestamps:
            raw_readings = []
            if interval == 'hourly':
                # Simulate 4 readings in the hour
                for _ in range(random.randint(1, 4)):
                    raw_readings.append(round(random.uniform(base_low - 2, base_high + 2), 1))
            elif interval == 'daily':
                # Simulate 24 readings for the day
                for _ in range(random.randint(20, 28)):
                    raw_readings.append(round(random.uniform(base_low - 3, base_high + 3), 1))
            elif interval == 'weekly':
                # Simulate 168 readings for the week
                for _ in range(random.randint(150, 180)):
                    raw_readings.append(round(random.uniform(base_low - 5, base_high + 5), 1))
            
            if aggregation == 'average':
                val = round(statistics.mean(raw_readings), 2) if raw_readings else None
            elif aggregation == 'median':
                val = round(statistics.median(raw_readings), 2) if raw_readings else None
            elif aggregation == 'min':
                val = round(min(raw_readings), 2) if raw_readings else None
            elif aggregation == 'max':
                val = round(max(raw_readings), 2) if raw_readings else None
            else:
                val = None
            
            series.append({
                'timestamp': ts.strftime('%Y-%m-%dT%H:%M:%S'),
                'value': val,
                'unit': _get_unit(metric),
                'readings_count': len(raw_readings)
            })
        
        result = {
            'patient_id': patient_id,
            'metric': metric,
            'interval': interval,
            'aggregation': aggregation,
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'data_points': series
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


def _get_unit(metric):
    units = {
        'heart_rate': 'bpm',
        'blood_pressure_systolic': 'mmHg',
        'blood_pressure_diastolic': 'mmHg',
        'temperature': '°C',
        'oxygen_saturation': '%',
        'respiratory_rate': 'breaths/min'
    }
    return units.get(metric, 'unknown')


TOOL_SPEC = {
    "name": "health_trend_viewer",
    "description": "Generate a time-series visualization dataset from patient vital signs records, aggregated by configurable time intervals, for monitoring health metric trends over days, weeks, or months.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier of the patient whose records are queried"
        },
        "metric": {
            "type": "string",
            "enum": [
                "heart_rate",
                "blood_pressure_systolic",
                "blood_pressure_diastolic",
                "temperature",
                "oxygen_saturation",
                "respiratory_rate"
            ],
            "description": "Health metric type for which the trend data is generated"
        },
        "interval": {
            "type": "string",
            "enum": [
                "hourly",
                "daily",
                "weekly"
            ],
            "description": "Time grouping interval for aggregation of raw readings"
        },
        "start_date": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
            "description": "Start date (inclusive) for the trend period in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
            "description": "End date (inclusive) for the trend period in YYYY-MM-DD format"
        },
        "aggregation": {
            "type": "string",
            "enum": [
                "average",
                "median",
                "min",
                "max"
            ],
            "description": "Optional: Statistical aggregation method applied to readings within each interval. Default is average."
        }
    },
    "required": [
        "patient_id",
        "metric",
        "interval",
        "start_date",
        "end_date"
    ]
},
}
