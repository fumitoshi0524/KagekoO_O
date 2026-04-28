"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a chronological timeline chart of patient vital signs over a date range."""
    import json
    from datetime import datetime, timedelta
    import random
    try:
        data = json.loads(payload)
        patient_id = data.get("patient_id")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if not patient_id or not start_date or not end_date:
            return json.dumps({"error": "Missing required fields: patient_id, start_date, end_date"}, ensure_ascii=False)
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."}, ensure_ascii=False)
        if end_dt < start_dt:
            return json.dumps({"error": "end_date must be after start_date."}, ensure_ascii=False)
        # Simulate patient record existence check (in production, query a database)
        if not patient_id.startswith("PAT"):
            return json.dumps({"error": f"Patient {patient_id} not found."}, ensure_ascii=False)
        vital_signs_param = data.get("vital_signs", ["heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic", "temperature", "respiratory_rate", "oxygen_saturation"])
        chart_type = data.get("chart_type", "multi_line")
        if chart_type not in ["line", "multi_line", "area", "scatter"]:
            chart_type = "multi_line"
        aggregation = data.get("aggregation", "raw")
        if aggregation not in ["raw", "hourly_avg", "daily_avg"]:
            aggregation = "raw"
        # Build simulated vital sign readings (real implementation would fetch from a medical records service)
        readings = []
        current = start_dt
        interval = timedelta(hours=1) if aggregation == "hourly_avg" else timedelta(days=1)
        if aggregation == "raw":
            interval = timedelta(hours=4)  # simulate 4-hourly readings
        while current <= end_dt:
            for vs in vital_signs_param:
                reading = {
                    "timestamp": current.isoformat(),
                    "vital_sign": vs,
                    "value": round(random.uniform(vital_sign_ranges.get(vs, [50, 100])[0], vital_sign_ranges.get(vs, [50, 100])[1]), 2),
                    "unit": vital_sign_units.get(vs, "")
                }
                readings.append(reading)
            current += interval
        # Generate chart configuration suitable for dashboard rendering
        chart_config = {
            "chart_type": chart_type,
            "aggregation": aggregation,
            "title": f"Vital Signs Timeline for Patient {patient_id}",
            "date_range": {"start": start_date, "end": end_date},
            "x_axis": {"label": "Timestamp", "field": "timestamp"},
            "y_axis": {"label": "Value", "field": "value"},
            "color_by": "vital_sign",
            "data": readings
        }
        return json.dumps(chart_config, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Failed to generate chart: {str(e)}"}, ensure_ascii=False)



TOOL_SPEC = {
    "name": "vital_signs_timeline_chart",
    "description": "Generate a chronological timeline chart of patient vital signs (heart rate, blood pressure, temperature, respiratory rate, oxygen saturation) over a specified date range, returning chart configuration data for display in a healthcare dashboard.",
    "category": "visualization",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient whose vital signs will be charted"
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the timeline in ISO 8601 format (YYYY-MM-DD). The chart will include readings from this date onward."
        },
        "end_date": {
            "type": "string",
            "description": "End date for the timeline in ISO 8601 format (YYYY-MM-DD). The chart will include readings up to this date."
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
                    "respiratory_rate",
                    "oxygen_saturation"
                ]
            },
            "description": "List of vital sign types to include in the chart. If not provided, all available vital signs are included."
        },
        "chart_type": {
            "type": "string",
            "enum": [
                "line",
                "multi_line",
                "area",
                "scatter"
            ],
            "description": "Optional: Type of chart to generate. Default is 'multi_line'. 'line' shows one vital sign at a time; 'multi_line' overlays multiple; 'area' fills below lines; 'scatter' plots discrete readings."
        },
        "aggregation": {
            "type": "string",
            "enum": [
                "raw",
                "hourly_avg",
                "daily_avg"
            ],
            "description": "Optional: Aggregation method for readings. 'raw' uses individual measurements; 'hourly_avg' computes hourly means; 'daily_avg' computes daily means. Default is 'raw'."
        }
    },
    "required": [
        "patient_id",
        "start_date",
        "end_date"
    ]
},
}
