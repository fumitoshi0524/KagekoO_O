"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import statistics
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        vital_signs = data.get('vital_signs', [])
        date_range = data.get('date_range', {})
        anomaly_threshold = data.get('anomaly_threshold', 2.0)

        if not patient_id:
            return json.dumps({'error': 'patient_id is required'}, ensure_ascii=False)
        if not vital_signs:
            return json.dumps({'error': 'at least one vital_sign must be specified'}, ensure_ascii=False)

        # Simulate patient record database lookup
        # In production, this would query EHR/EMR system
        today = datetime.now()
        if date_range and 'start' in date_range and 'end' in date_range:
            start_date = datetime.strptime(date_range['start'], '%Y-%m-%d')
            end_date = datetime.strptime(date_range['end'], '%Y-%m-%d')
        else:
            start_date = today - timedelta(days=30)
            end_date = today

        # Generate realistic mock data for each vital sign
        mock_data = {
            'heart_rate': [72, 75, 68, 80, 74, 71, 69, 77, 73, 70, 150, 72, 76, 68, 73, 71, 75, 69, 74, 72, 73, 70, 78, 72, 69, 74, 76, 71, 73, 72],
            'blood_pressure_systolic': [120, 118, 122, 115, 125, 119, 121, 117, 123, 120, 180, 119, 121, 116, 124, 120, 118, 122, 119, 121, 120, 117, 123, 119, 121, 120, 118, 122, 121, 120],
            'blood_pressure_diastolic': [80, 78, 82, 75, 85, 79, 81, 77, 83, 80, 95, 79, 81, 76, 84, 80, 78, 82, 79, 81, 80, 77, 83, 79, 81, 80, 78, 82, 81, 80],
            'temperature': [36.5, 36.7, 36.6, 36.8, 36.4, 36.9, 36.5, 36.7, 36.6, 36.5, 39.2, 36.6, 36.8, 36.5, 36.7, 36.6, 36.9, 36.5, 36.7, 36.6, 36.5, 36.8, 36.6, 36.7, 36.5, 36.9, 36.6, 36.7, 36.5, 36.8],
            'respiratory_rate': [16, 15, 17, 14, 18, 16, 15, 17, 16, 15, 28, 16, 17, 15, 16, 15, 18, 16, 17, 15, 16, 14, 17, 16, 15, 16, 17, 15, 16, 15],
            'oxygen_saturation': [98, 97, 99, 98, 97, 99, 98, 97, 98, 99, 92, 98, 97, 99, 98, 97, 99, 98, 97, 98, 99, 97, 98, 99, 98, 97, 99, 98, 97, 98]
        }

        results = {}
        for vs in vital_signs:
            if vs not in mock_data:
                results[vs] = {'error': f'Unsupported vital sign: {vs}'}
                continue

            readings = mock_data[vs][:30]  # Simulate 30 readings
            n = len(readings)
            if n < 2:
                results[vs] = {'error': 'Insufficient data for analysis (minimum 2 readings required)'}
                continue

            mean = statistics.mean(readings)
            stdev = statistics.stdev(readings) if n > 1 else 0.0
            min_val = min(readings)
            max_val = max(readings)
            median = statistics.median(readings)

            # Trend direction: compare first half average to second half average
            half = n // 2
            first_half_avg = statistics.mean(readings[:half])
            second_half_avg = statistics.mean(readings[half:])
            difference = second_half_avg - first_half_avg
            if abs(difference) < 0.1 * mean:  # less than 10% change
                trend = 'stable'
            elif difference > 0:
                trend = 'increasing'
            else:
                trend = 'decreasing'

            # Anomaly detection using Z-score threshold
            anomalies = []
            for i, val in enumerate(readings):
                z_score = abs(val - mean) / stdev if stdev > 0 else 0
                if z_score > anomaly_threshold:
                    anomalies.append({
                        'index': i,
                        'value': val,
                        'z_score': round(z_score, 2)
                    })

            results[vs] = {
                'readings_count': n,
                'statistics': {
                    'mean': round(mean, 2),
                    'median': median,
                    'stdev': round(stdev, 2),
                    'min': min_val,
                    'max': max_val
                },
                'trend': {
                    'direction': trend,
                    'first_half_avg': round(first_half_avg, 2),
                    'second_half_avg': round(second_half_avg, 2),
                    'change': round(difference, 2)
                },
                'anomalies': {
                    'count': len(anomalies),
                    'threshold': anomaly_threshold,
                    'flagged_readings': anomalies
                },
                'clinical_implications': {
                    'stable': 'Normal fluctuation within expected range',
                    'increasing': 'Potential deterioration; recommend escalation of monitoring',
                    'decreasing': 'May indicate improvement or overcompensation; evaluate treatment efficacy'
                }.get(trend, 'Unable to determine clinical implications')
            }

        return json.dumps({
            'patient_id': patient_id,
            'analysis_period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'vital_sign_analyses': results,
            'overall_assessment': {
                'total_anomalies': sum(len(r.get('anomalies', {}).get('flagged_readings', [])) for r in results.values() if isinstance(r, dict)),
                'patient_status': 'critical' if any(r.get('trend', {}).get('direction') == 'increasing' and r.get('anomalies', {}).get('count', 0) > 0 for r in results.values() if isinstance(r, dict)) else 'monitor' if any(r.get('trend', {}).get('direction') != 'stable' for r in results.values() if isinstance(r, dict)) else 'stable'
            }
        }, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Analysis error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "patient_trend_analysis",
    "description": "Analyze historical patient vital sign records to identify trends, detect anomalies, and calculate statistical summaries for clinical decision support. Returns trend direction, anomaly flags, and aggregated statistics per vital sign type.",
    "category": "analysis",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient whose records are analyzed (alphanumeric, max 20 characters)."
        },
        "vital_signs": {
            "type": "array",
            "description": "List of vital sign type codes to analyze. Supported types: heart_rate (HR), blood_pressure_systolic (BP_SYS), blood_pressure_diastolic (BP_DIA), temperature (TEMP), respiratory_rate (RR), oxygen_saturation (SpO2).",
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
        "date_range": {
            "type": "object",
            "description": "Optional: Time window for the analysis. If omitted, defaults to last 30 days.",
            "properties": {
                "start": {
                    "type": "string",
                    "description": "Start date in ISO 8601 format (YYYY-MM-DD). Must be before end date."
                },
                "end": {
                    "type": "string",
                    "description": "End date in ISO 8601 format (YYYY-MM-DD). Must be after start date."
                }
            },
            "required": []
        },
        "anomaly_threshold": {
            "type": "number",
            "description": "Optional: Standard deviation multiplier for anomaly detection (default 2.0, range 1.0-5.0). Higher values flag fewer anomalies."
        }
    },
    "required": [
        "patient_id",
        "vital_signs"
    ]
},
}
