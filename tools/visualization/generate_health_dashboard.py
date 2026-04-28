"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        if not patient_id:
            return json.dumps({'error': 'patient_id is required'}, ensure_ascii=False)
        vitals = data.get('vitals', {})
        if not vitals:
            return json.dumps({'error': 'vitals object is required'}, ensure_ascii=False)
        lab_results = data.get('lab_results', {})
        display_options = data.get('display_options', {})
        show_alerts_only = display_options.get('show_alerts_only', False)
        color_theme = display_options.get('color_theme', 'clinical')

        # Define normal ranges (illustrative)
        vitals_thresholds = {
            'heart_rate': (60, 100),
            'blood_pressure_systolic': (90, 140),
            'blood_pressure_diastolic': (60, 90),
            'temperature': (36.0, 37.5),
            'oxygen_saturation': (95, 100)
        }
        lab_thresholds = {
            'glucose': (70, 140),
            'hemoglobin': (12, 16),
            'white_blood_cell_count': (4.0, 11.0),
            'creatinine': (0.6, 1.2)
        }

        alerts = []
        vitals_display = []
        for key, value in vitals.items():
            if key not in vitals_thresholds:
                continue
            lo, hi = vitals_thresholds[key]
            flag = 'normal'
            if value < lo:
                flag = 'low'
                alerts.append(f'Vital {key} is low: {value}')
            elif value > hi:
                flag = 'high'
                alerts.append(f'Vital {key} is high: {value}')
            vitals_display.append({'name': key, 'value': value, 'status': flag, 'thresholds': {'normal_low': lo, 'normal_high': hi}})

        lab_display = []
        for key, value in lab_results.items():
            if key not in lab_thresholds:
                continue
            lo, hi = lab_thresholds[key]
            flag = 'normal'
            if value < lo:
                flag = 'low'
                alerts.append(f'Lab {key} is low: {value}')
            elif value > hi:
                flag = 'high'
                alerts.append(f'Lab {key} is high: {value}')
            lab_display.append({'name': key, 'value': value, 'status': flag, 'thresholds': {'normal_low': lo, 'normal_high': hi}})

        dashboard = {
            'patient_id': patient_id,
            'color_theme': color_theme,
            'timestamp': '2025-04-05T10:30:00Z',  # simulated timestamp
            'alerts': alerts,
            'summary': {
                'total_alerts': len(alerts),
                'vitals_count': len(vitals_display),
                'lab_results_count': len(lab_display)
            }
        }

        if show_alerts_only:
            dashboard['vitals'] = [v for v in vitals_display if v['status'] != 'normal']
            dashboard['lab_results'] = [l for l in lab_display if l['status'] != 'normal']
        else:
            dashboard['vitals'] = vitals_display
            dashboard['lab_results'] = lab_display

        return json.dumps(dashboard, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_health_dashboard",
    "description": "Creates a JSON-based health monitoring dashboard summarizing key patient vitals, lab results, and alert flags for a given patient record, intended for clinical review or integration into a healthcare visualization system.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., medical record number). Must be non-empty.",
            "examples": [
                "PT-78901",
                "MRN-4423"
            ]
        },
        "vitals": {
            "type": "object",
            "description": "Object containing key vital signs. Allowed keys: heart_rate (bpm), blood_pressure_systolic (mmHg), blood_pressure_diastolic (mmHg), temperature (Celsius), oxygen_saturation (%).",
            "properties": {
                "heart_rate": {
                    "type": "number",
                    "description": "Heart rate in beats per minute (bpm)."
                },
                "blood_pressure_systolic": {
                    "type": "number",
                    "description": "Systolic blood pressure in mmHg."
                },
                "blood_pressure_diastolic": {
                    "type": "number",
                    "description": "Diastolic blood pressure in mmHg."
                },
                "temperature": {
                    "type": "number",
                    "description": "Body temperature in degrees Celsius."
                },
                "oxygen_saturation": {
                    "type": "number",
                    "description": "Blood oxygen saturation as a percentage (0-100)."
                }
            },
            "additionalProperties": False,
            "examples": [
                {
                    "heart_rate": 72,
                    "blood_pressure_systolic": 120,
                    "blood_pressure_diastolic": 80,
                    "temperature": 36.6,
                    "oxygen_saturation": 98
                }
            ]
        },
        "lab_results": {
            "type": "object",
            "description": "Object containing lab test results. Allowed keys: glucose (mg/dL), hemoglobin (g/dL), white_blood_cell_count (x10^9/L), creatinine (mg/dL).",
            "properties": {
                "glucose": {
                    "type": "number",
                    "description": "Blood glucose level in mg/dL."
                },
                "hemoglobin": {
                    "type": "number",
                    "description": "Hemoglobin level in g/dL."
                },
                "white_blood_cell_count": {
                    "type": "number",
                    "description": "White blood cell count in x10^9/L."
                },
                "creatinine": {
                    "type": "number",
                    "description": "Creatinine level in mg/dL."
                }
            },
            "additionalProperties": False,
            "examples": [
                {
                    "glucose": 95,
                    "hemoglobin": 14.5,
                    "white_blood_cell_count": 7.2,
                    "creatinine": 0.9
                }
            ]
        },
        "display_options": {
            "type": "object",
            "description": "Optional: Configuration for dashboard output. Keys: show_alerts_only (boolean, default False) – if True, returns only flagged items; color_theme (string, default 'clinical') – supports 'clinical' (blue/gray) or 'emergency' (red/orange).",
            "properties": {
                "show_alerts_only": {
                    "type": "boolean",
                    "description": "Optional: If True, only alert items are included in the dashboard."
                },
                "color_theme": {
                    "type": "string",
                    "enum": [
                        "clinical",
                        "emergency"
                    ],
                    "description": "Optional: Color theme for the dashboard."
                }
            },
            "additionalProperties": False
        }
    },
    "required": [
        "patient_id",
        "vitals"
    ]
},
}
