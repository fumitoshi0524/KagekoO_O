"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        required = ["patient_id", "age", "gender", "previous_admissions", "diagnosis_code", "length_of_stay"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"})
        pid = data["patient_id"]
        age = int(data["age"])
        gender = data["gender"]
        prev_adm = int(data["previous_admissions"])
        los = int(data["length_of_stay"])
        dx = data["diagnosis_code"]
        comorbidities = data.get("comorbidities", [])
        # Simple risk scoring logic
        score = 0
        if age >= 65:
            score += 2
        if prev_adm >= 2:
            score += 3
        if los > 7:
            score += 2
        # High-risk diagnosis categories (simplified)
        high_risk_dx_prefixes = ["I", "J", "N", "R"]
        if dx and dx[0] in high_risk_dx_prefixes:
            score += 2
        score += len(comorbidities)
        if score <= 3:
            risk = "low"
        elif score <= 6:
            risk = "moderate"
        else:
            risk = "high"
        contrib = []
        if age >= 65:
            contrib.append("age >= 65")
        if prev_adm >= 2:
            contrib.append("frequent prior admissions")
        if los > 7:
            contrib.append("prolonged length of stay")
        if dx and dx[0] in high_risk_dx_prefixes:
            contrib.append(f"high-risk diagnosis category ({dx[0]})")
        for c in comorbidities:
            contrib.append(f"comorbidity: {c}")
        result = {
            "patient_id": pid,
            "readmission_risk": risk,
            "risk_score": score,
            "contributing_factors": contrib
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "readmission_risk_analyzer",
    "description": "Analyze patient hospital readmission risk based on admission history, diagnosis codes, and demographic data, returning a risk score (low, moderate, high) and a list of contributing factors.",
    "category": "analysis",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., MRN or UUID)."
        },
        "age": {
            "type": "integer",
            "description": "Patient age in years (0-120)."
        },
        "gender": {
            "type": "string",
            "enum": [
                "male",
                "female",
                "other"
            ],
            "description": "Patient gender."
        },
        "previous_admissions": {
            "type": "integer",
            "description": "Number of hospital admissions in the past 12 months."
        },
        "diagnosis_code": {
            "type": "string",
            "description": "Primary ICD-10 diagnosis code for the current admission (e.g., 'I10' for hypertension)."
        },
        "length_of_stay": {
            "type": "integer",
            "description": "Current length of hospital stay in days (>= 1)."
        },
        "comorbidities": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of known chronic condition ICD-10 codes (e.g., ['E11', 'J45'])."
        }
    },
    "required": [
        "patient_id",
        "age",
        "gender",
        "previous_admissions",
        "diagnosis_code",
        "length_of_stay"
    ]
},
}
