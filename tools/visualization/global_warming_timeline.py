"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        start_year = data.get('start_year')
        end_year = data.get('end_year')
        baseline_start = data.get('baseline_start', 1850)
        baseline_end = data.get('baseline_end', 1900)
        smoothing = data.get('smoothing', 0)

        if not start_year or not end_year:
            return json.dumps({'error': 'start_year and end_year are required'})
        if not isinstance(start_year, int) or not isinstance(end_year, int):
            return json.dumps({'error': 'start_year and end_year must be integers'})
        if start_year < 1850 or end_year > 2024:
            return json.dumps({'error': 'Years must be between 1850 and 2024'})
        if start_year > end_year:
            return json.dumps({'error': 'start_year must be <= end_year'})
        if not isinstance(baseline_start, int) or not isinstance(baseline_end, int):
            return json.dumps({'error': 'baseline_start and baseline_end must be integers'})
        if baseline_start < 1850 or baseline_end > 1900:
            return json.dumps({'error': 'Baseline years must be between 1850 and 1900'})
        if baseline_start > baseline_end:
            return json.dumps({'error': 'baseline_start must be <= baseline_end'})
        if not isinstance(smoothing, int) or smoothing < 0 or smoothing > 20:
            return json.dumps({'error': 'smoothing must be integer between 0 and 20'})

        # Simulated global temperature anomaly data (1850-2024) relative to 1850-1900 baseline
        # Real data would come from a database; here we generate realistic yearly values
        import math
        import random
        random.seed(42)  # deterministic for consistency
        raw_data = []
        for year in range(1850, 2025):
            # base anomaly: linear trend from -0.4 in 1850 to 1.2 in 2024 (Celsius)
            base = -0.4 + (year - 1850) * (1.6 / 174)
            # add natural variability (noise)
            noise = random.gauss(0, 0.08)
            anomaly = round(base + noise, 3)
            raw_data.append({'year': year, 'anomaly': anomaly})

        # Compute baseline average from raw_data
        baseline_sum = 0
        baseline_count = 0
        for d in raw_data:
            if baseline_start <= d['year'] <= baseline_end:
                baseline_sum += d['anomaly']
                baseline_count += 1
        if baseline_count == 0:
            return json.dumps({'error': 'No data for baseline period'})
        baseline_avg = baseline_sum / baseline_count

        # Adjust anomalies relative to baseline
        for d in raw_data:
            d['anomaly'] = round(d['anomaly'] - baseline_avg, 3)

        # Filter requested range
        filtered = [d for d in raw_data if start_year <= d['year'] <= end_year]
        if not filtered:
            return json.dumps({'error': 'No data in the specified year range'})

        # Apply smoothing if requested
        if smoothing > 1:
            values = [d['anomaly'] for d in filtered]
            half_window = smoothing // 2
            smoothed = []
            for i in range(len(values)):
                start_idx = max(0, i - half_window)
                end_idx = min(len(values), i + half_window + 1)
                avg = sum(values[start_idx:end_idx]) / (end_idx - start_idx)
                smoothed.append(round(avg, 3))
            for i, d in enumerate(filtered):
                d['anomaly'] = smoothed[i]

        # Build result
        result = {
            'chart_type': 'line',
            'title': f'Global Average Temperature Anomaly ({start_year}-{end_year})',
            'x_axis': {'label': 'Year', 'data': [d['year'] for d in filtered]},
            'y_axis': {'label': 'Temperature Anomaly (°C)', 'unit': '°C'},
            'series': [
                {
                    'name': 'Annual Anomaly',
                    'data': [d['anomaly'] for d in filtered]
                }
            ],
            'metadata': {
                'baseline_period': f'{baseline_start}-{baseline_end}',
                'smoothing': smoothing if smoothing > 1 else 'none',
                'data_points': len(filtered),
                'min_anomaly': min(d['anomaly'] for d in filtered),
                'max_anomaly': max(d['anomaly'] for d in filtered),
                'mean_anomaly': round(sum(d['anomaly'] for d in filtered) / len(filtered), 3)
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})



TOOL_SPEC = {
    "name": "global_warming_timeline",
    "description": "Generates a time-series visualization of global average temperature anomalies relative to a pre-industrial baseline, returning a JSON structure that can be rendered as a line chart by a client-side charting library.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "start_year": {
            "type": "integer",
            "description": "The first year of the data range (inclusive, must be >= 1850).",
            "minimum": 1850,
            "maximum": 2024
        },
        "end_year": {
            "type": "integer",
            "description": "The last year of the data range (inclusive, must be >= start_year and <= 2024).",
            "minimum": 1850,
            "maximum": 2024
        },
        "baseline_start": {
            "type": "integer",
            "description": "Optional: The start year for the pre-industrial baseline period (default 1850).",
            "default": 1850,
            "minimum": 1850,
            "maximum": 1900
        },
        "baseline_end": {
            "type": "integer",
            "description": "Optional: The end year for the pre-industrial baseline period (default 1900).",
            "default": 1900,
            "minimum": 1850,
            "maximum": 1900
        },
        "smoothing": {
            "type": "integer",
            "description": "Optional: Number of years for moving average smoothing (0 disables smoothing, default 0).",
            "default": 0,
            "minimum": 0,
            "maximum": 20
        }
    },
    "required": [
        "start_year",
        "end_year"
    ]
},
}
