"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a line chart visualization of patient vital signs over time."""
    import json
    try:
        data = json.loads(payload)
        patient_id = data.get("patient_id")
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        vital_signs = data.get("vital_signs", [])
        chart_type = data.get("chart_type", "line")
        aggregation = data.get("aggregation", "raw")
        
        if not patient_id or not date_from or not date_to or not vital_signs:
            return json.dumps({"error": "Missing required fields: patient_id, date_from, date_to, vital_signs"}, ensure_ascii=False)
        
        # Simulated vital signs database (in real scenario, this would query EHR/EMR system)
        mock_vital_records = [
            {"timestamp": "2025-03-01T08:00:00", "heart_rate": 72, "blood_pressure_systolic": 120, "blood_pressure_diastolic": 80, "temperature": 36.8, "respiratory_rate": 16, "oxygen_saturation": 98},
            {"timestamp": "2025-03-01T12:00:00", "heart_rate": 75, "blood_pressure_systolic": 118, "blood_pressure_diastolic": 78, "temperature": 37.0, "respiratory_rate": 18, "oxygen_saturation": 97},
            {"timestamp": "2025-03-01T16:00:00", "heart_rate": 80, "blood_pressure_systolic": 125, "blood_pressure_diastolic": 82, "temperature": 37.2, "respiratory_rate": 20, "oxygen_saturation": 96},
            {"timestamp": "2025-03-02T08:00:00", "heart_rate": 68, "blood_pressure_systolic": 115, "blood_pressure_diastolic": 75, "temperature": 36.6, "respiratory_rate": 14, "oxygen_saturation": 99},
            {"timestamp": "2025-03-02T12:00:00", "heart_rate": 73, "blood_pressure_systolic": 122, "blood_pressure_diastolic": 79, "temperature": 36.9, "respiratory_rate": 17, "oxygen_saturation": 98}
        ]
        
        # Filter by date range
        filtered_records = [r for r in mock_vital_records if date_from <= r["timestamp"][:10] <= date_to]
        
        if not filtered_records:
            return json.dumps({"error": "No vital sign records found for the specified period"}, ensure_ascii=False)
        
        # Build time series data
        timestamps = [r["timestamp"] for r in filtered_records]
        series = {}
        for vs in vital_signs:
            vs_key = vs.replace("blood_pressure_", "").replace("_", "_")
            series[vs] = []
            for r in filtered_records:
                if vs in r:
                    series[vs].append(r[vs])
                else:
                    series[vs].append(None)
        
        # Apply aggregation if needed
        if aggregation == "hourly_average":
            # Simplified: just take the values as-is for mock
            pass
        elif aggregation == "daily_average":
            # Mock: calculate daily average
            daily_data = {}
            for r in filtered_records:
                day = r["timestamp"][:10]
                if day not in daily_data:
                    daily_data[day] = {vs: [] for vs in vital_signs}
                for vs in vital_signs:
                    if vs in r:
                        daily_data[day][vs].append(r[vs])
            timestamps = sorted(daily_data.keys())
            series = {vs: [] for vs in vital_signs}
            for day in timestamps:
                for vs in vital_signs:
                    vals = daily_data[day][vs]
                    if vals:
                        series[vs].append(sum(vals) / len(vals))
                    else:
                        series[vs].append(None)
        
        # Build chart data structure
        chart_config = {
            "chart_type": chart_type,
            "title": f"Vital Signs Trend for Patient {patient_id}",
            "x_axis": {"label": "Timestamp", "data": timestamps},
            "y_axis": {"label": "Value"},
            "series": []
        }
        
        vs_labels = {
            "heart_rate": "Heart Rate (bpm)",
            "blood_pressure_systolic": "Systolic BP (mmHg)",
            "blood_pressure_diastolic": "Diastolic BP (mmHg)",
            "temperature": "Temperature (°C)",
            "respiratory_rate": "Respiratory Rate (breaths/min)",
            "oxygen_saturation": "Oxygen Saturation (%)"
        }
        
        for vs in vital_signs:
            chart_config["series"].append({
                "name": vs_labels.get(vs, vs),
                "data": series[vs],
                "unit": vs_labels.get(vs, "")
            })
        
        # Generate a simple SVG-like data URI for the chart (in real scenario, this would be rendered)
        result = {
            "status": "success",
            "patient_id": patient_id,
            "period": {"from": date_from, "to": date_to},
            "chart": chart_config,
            "total_records": len(filtered_records),
            "vital_signs_included": vital_signs
        }
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Failed to generate visualization: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "vital_signs_visualizer",
    "description": "Generate a line chart visualization of patient vital signs (heart rate, blood pressure, temperature, respiratory rate) over time from monitoring records to support clinical trend analysis.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient whose vital signs are to be charted"
        },
        "date_from": {
            "type": "string",
            "description": "Start date of the monitoring period in YYYY-MM-DD format"
        },
        "date_to": {
            "type": "string",
            "description": "End date of the monitoring period in YYYY-MM-DD format"
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
        "chart_type": {
            "type": "string",
            "description": "Optional: Type of chart to generate (default is line chart)",
            "enum": [
                "line",
                "scatter",
                "area"
            ],
            "default": "line"
        },
        "aggregation": {
            "type": "string",
            "description": "Optional: Time aggregation level for data points",
            "enum": [
                "raw",
                "hourly_average",
                "daily_average"
            ],
            "default": "raw"
        }
    },
    "required": [
        "patient_id",
        "date_from",
        "date_to",
        "vital_signs"
    ]
},
}
