"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Organize and annotate raw scientific experiment data by assigning metadata tags and grouping related measurements."""
    import json
    import uuid
    from datetime import datetime

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ["experiment_name", "research_group", "phase", "condition", "raw_measurements"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"})

        # Validate replicate if provided
        replicate = data.get("replicate", 1)
        if not isinstance(replicate, int) or replicate < 1:
            return json.dumps({"error": "replicate must be an integer >= 1"})

        # Validate phase
        valid_phases = ["pilot", "calibration", "main", "validation", "follow_up"]
        if data["phase"] not in valid_phases:
            return json.dumps({"error": f"Invalid phase. Must be one of: {valid_phases}"})

        # Validate measurements
        measurements = data["raw_measurements"]
        if not isinstance(measurements, list) or len(measurements) == 0:
            return json.dumps({"error": "raw_measurements must be a non-empty array"})

        for i, m in enumerate(measurements):
            if not all(k in m for k in ("measurement_type", "value", "unit")):
                return json.dumps({"error": f"Measurement at index {i} missing required keys"})
            if not isinstance(m["value"], (int, float)):
                return json.dumps({"error": f"Measurement at index {i} value must be numeric"})

        # Generate unique experiment identifier
        experiment_id = str(uuid.uuid4())

        # Count fields and types
        meas_types = {}
        for m in measurements:
            mt = m["measurement_type"]
            meas_types[mt] = meas_types.get(mt, 0) + 1

        field_counts = {}
        field_counts["experiment_name"] = 1
        field_counts["measurement_entries"] = len(measurements)
        field_counts["unique_measurement_types"] = len(meas_types)
        for mt, count in meas_types.items():
            field_counts[f"measurement_type_{mt}_count"] = count

        # Compute min, max, mean per measurement type
        meas_stats = {}
        for mt in meas_types:
            values = [m["value"] for m in measurements if m["measurement_type"] == mt]
            meas_stats[mt] = {
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values)
            }

        # Build curated record
        curated_record = {
            "experiment_id": experiment_id,
            "experiment_name": data["experiment_name"],
            "research_group": data["research_group"],
            "phase": data["phase"],
            "condition": data["condition"],
            "replicate": replicate,
            "curation_timestamp": datetime.utcnow().isoformat() + "Z",
            "raw_measurement_count": len(measurements),
            "measurement_type_distribution": meas_types,
            "measurement_statistics": meas_stats,
            "field_counts": field_counts
        }

        return json.dumps(curated_record, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


TOOL_SPEC = {
    "name": "experiment_data_curator",
    "description": "Organize and annotate raw scientific experiment data by assigning metadata tags (phase, condition, replicate) and grouping related measurements into a structured experiment record. Returns a curated dataset summary with field counts and a unique experiment identifier for downstream analysis or reporting.",
    "category": "operations",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "experiment_name": {
            "type": "string",
            "description": "Descriptive name of the experiment (e.g., 'Enzyme Kinetics Trial 4')"
        },
        "research_group": {
            "type": "string",
            "description": "Principal investigator or group owning the experiment"
        },
        "phase": {
            "type": "string",
            "enum": [
                "pilot",
                "calibration",
                "main",
                "validation",
                "follow_up"
            ],
            "description": "Phase of the scientific study this experiment belongs to"
        },
        "condition": {
            "type": "string",
            "description": "Controlled condition or variable tested (e.g., 'pH 7.2', 'temperature 37C')"
        },
        "replicate": {
            "type": "integer",
            "description": "Replicate number for this experiment (>= 1)"
        },
        "raw_measurements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "measurement_type": {
                        "type": "string",
                        "description": "Type of measurement (e.g., 'absorbance', 'concentration')"
                    },
                    "value": {
                        "type": "number",
                        "description": "Numeric measurement value"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measurement (e.g., 'mg/mL', 'AU')"
                    }
                },
                "required": [
                    "measurement_type",
                    "value",
                    "unit"
                ]
            },
            "description": "Array of raw measurement objects with type, value, and unit"
        }
    },
    "required": [
        "experiment_name",
        "research_group",
        "phase",
        "condition",
        "raw_measurements"
    ]
},
}
