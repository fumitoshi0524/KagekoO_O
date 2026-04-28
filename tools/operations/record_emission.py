"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Record a greenhouse gas emission event for a facility."""
    import json
    from datetime import datetime, timezone
    import uuid
    try:
        data = json.loads(payload)
        facility_id = data.get("facility_id")
        gas_type = data.get("gas_type")
        quantity_kg = data.get("quantity_kg")
        source_category = data.get("source_category")
        if not facility_id or not gas_type or quantity_kg is None or not source_category:
            return json.dumps({"error": "Missing required fields: facility_id, gas_type, quantity_kg, source_category"})
        valid_gases = ["CO2", "CH4", "N2O", "SF6", "HFCs", "PFCs", "NF3"]
        if gas_type not in valid_gases:
            return json.dumps({"error": f"Invalid gas_type: {gas_type}. Must be one of {valid_gases}"})
        if not isinstance(quantity_kg, (int, float)) or quantity_kg <= 0:
            return json.dumps({"error": "quantity_kg must be a positive number"})
        valid_sources = ["stationary_combustion", "mobile_combustion", "fugitive", "process", "waste", "agriculture", "land_use"]
        if source_category not in valid_sources:
            return json.dumps({"error": f"Invalid source_category: {source_category}. Must be one of {valid_sources}"})
        event_time = data.get("timestamp")
        if not event_time:
            event_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            try:
                datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                return json.dumps({"error": "Invalid timestamp format, expected YYYY-MM-DDTHH:MM:SSZ"})
        emission_id = str(uuid.uuid4())
        result = {
            "emission_id": emission_id,
            "facility_id": facility_id,
            "gas_type": gas_type,
            "quantity_kg": quantity_kg,
            "source_category": source_category,
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "recorded"
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"error: {e}"


TOOL_SPEC = {
    "name": "record_emission",
    "description": "Record a greenhouse gas emission event for a facility, including emission type, estimated quantity, and source category, and return a confirmation with a unique emission ID and timestamp for compliance tracking.",
    "category": "operations",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "facility_id": {
            "type": "string",
            "description": "Unique identifier for the facility emitting the gas (e.g., plant code or site ID)."
        },
        "gas_type": {
            "type": "string",
            "description": "Type of greenhouse gas being emitted.",
            "enum": [
                "CO2",
                "CH4",
                "N2O",
                "SF6",
                "HFCs",
                "PFCs",
                "NF3"
            ]
        },
        "quantity_kg": {
            "type": "number",
            "description": "Estimated mass of gas emitted in kilograms (must be positive)."
        },
        "source_category": {
            "type": "string",
            "description": "Broad emission source category.",
            "enum": [
                "stationary_combustion",
                "mobile_combustion",
                "fugitive",
                "process",
                "waste",
                "agriculture",
                "land_use"
            ]
        },
        "timestamp": {
            "type": "string",
            "description": "Optional: ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SSZ) of the emission event. Default is current UTC time if not provided."
        }
    },
    "required": [
        "facility_id",
        "gas_type",
        "quantity_kg",
        "source_category"
    ]
},
}
