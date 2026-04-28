"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a patient vitals dashboard JSON."""
    import json
    import random
    import datetime

    try:
        data = json.loads(payload)
        patient_id = data.get("patient_id")
        time_range = data.get("time_range")

        if not patient_id or not time_range:
            return json.dumps({"error": "Missing required parameters: patient_id and time_range"})

        # Simulate fetching vital signs data from a medical records system
        now = datetime.datetime.utcnow()
        range_map = {"last_24h": 1440, "last_7d": 10080, "last_30d": 43200, "last_90d": 129600}
        total_minutes = range_map.get(time_range, 1440)
        interval_minutes = max(1, total_minutes // 50)  # sample ~50 points for visualization

        selected_vitals = data.get("vital_signs", ["heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic", "temperature", "oxygen_saturation", "respiratory_rate"])
        include_alerts = data.get("include_alerts", False)

        vitals_data = {}
        alerts = []

        for vital in selected_vitals:
            timestamps = []
            values = []
            for i in range(0, total_minutes, interval_minutes):
                ts = now - datetime.timedelta(minutes=i)
                timestamps.append(ts.isoformat())
                if vital == "heart_rate":
                    value = random.randint(50, 120)
                    if include_alerts and (value < 60 or value > 100):
                        alerts.append({"timestamp": ts.isoformat(), "vital": vital, "value": value, "alert": "Abnormal heart rate"})
                elif vital == "blood_pressure_systolic":
                    value = random.randint(90, 180)
                    if include_alerts and (value < 100 or value > 160):
                        alerts.append({"timestamp": ts.isoformat(), "vital": vital, "value": value, "alert": "Abnormal systolic BP"})
                elif vital == "blood_pressure_diastolic":
                    value = random.randint(60, 110)
                    if include_alerts and (value < 60 or value > 100):
                        alerts.append({"timestamp": ts.isoformat(), "vital": vital, "value": value, "alert": "Abnormal diastolic BP"})
                elif vital == "temperature":
                    value = round(random.uniform(35.5, 40.0), 1)
                    if include_alerts and (value < 36.0 or value > 38.5):
                        alerts.append({"timestamp": ts.isoformat(), "vital": vital, "value": value, "alert": "Abnormal temperature"})
                elif vital == "oxygen_saturation":
                    value = random.randint(88, 100)
                    if include_alerts and (value < 95):
                        alerts.append({"timestamp": ts.isoformat(), "vital": vital, "value": value, "alert": "Low oxygen saturation"})
                elif vital == "respiratory_rate":
                    value = random.randint(10, 25)
                    if include_alerts and (value < 12 or value > 20):
                        alerts.append({"timestamp": ts.isoformat(), "vital": vital, "value": value, "alert": "Abnormal respiratory rate"})
                else:
                    value = 0
                values.append(value)
            vitals_data[vital] = {"timestamps": timestamps[::-1], "values": values[::-1]}

        result = {
            "patient_id": patient_id,
            "time_range": time_range,
            "chart_data": vitals_data,
            "meta": {
                "number_of_data_points_per_vital": len(vitals_data.get(selected_vitals[0], {}).get("timestamps", [])),
                "measurement_unit": {
                    "heart_rate": "bpm",
                    "blood_pressure_systolic": "mmHg",
                    "blood_pressure_diastolic": "mmHg",
                    "temperature": "Celsius",
                    "oxygen_saturation": "%",
                    "respiratory_rate": "breaths/min"
                }
            }
        }

        if include_alerts and alerts:
            result["alerts"] = alerts

        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"Failed to generate dashboard: {str(e)}"})


TOOL_SPEC = {
    "name": "patient_vitals_dashboard",
    "description": "Generate an interactive dashboard visualization of patient vital signs (heart rate, blood pressure, temperature, oxygen saturation, respiratory rate) over time, returning a JSON structure suitable for rendering chart components in a healthcare monitoring application.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient whose vitals are to be visualized.",
            "examples": [
                "P12345",
                "PT-67890"
            ]
        },
        "time_range": {
            "type": "string",
            "enum": [
                "last_24h",
                "last_7d",
                "last_30d",
                "last_90d"
            ],
            "description": "Time range for the vital signs data to include in the dashboard."
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
                    "oxygen_saturation",
                    "respiratory_rate"
                ]
            },
            "description": "Optional: List of vital signs to include. If omitted, all available vital signs are included.",
            "examples": [
                [
                    "heart_rate",
                    "blood_pressure_systolic"
                ]
            ]
        },
        "include_alerts": {
            "type": "boolean",
            "description": "Optional: If True, flag abnormal readings (e.g., heart rate < 60 or > 100) in the output for clinical attention."
        }
    },
    "required": [
        "patient_id",
        "time_range"
    ]
},
}
