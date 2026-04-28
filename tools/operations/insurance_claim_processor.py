"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Process a healthcare insurance claim by validating patient coverage, calculating patient responsibility versus insurance payout, and determining if the claim should be approved or denied based on policy rules and service codes."""
    import json
    from datetime import datetime

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ["patient_id", "insurance_plan", "service_code", "service_cost", "date_of_service"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)

        patient_id = data["patient_id"]
        insurance_plan = data["insurance_plan"]
        service_code = data["service_code"]
        service_cost = data["service_cost"]
        date_of_service = data["date_of_service"]
        deductible_met = data.get("deductible_met", 0)
        plan_type = data.get("plan_type", "PPO")

        # Validate service_cost is positive
        if service_cost < 0:
            return json.dumps({"error": "service_cost must be non-negative"}, ensure_ascii=False)

        # Validate date format
        try:
            datetime.strptime(date_of_service, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Invalid date_of_service format. Must be YYYY-MM-DD"}, ensure_ascii=False)

        # Validate plan_type
        valid_plans = ["HMO", "PPO", "EPO", "POS", "HDHP"]
        if plan_type not in valid_plans:
            return json.dumps({"error": f"Invalid plan_type. Must be one of: {valid_plans}"}, ensure_ascii=False)

        # Define deductible and co-insurance rates by plan type
        plan_params = {
            "HMO":  {"deductible": 1000, "coinsurance_rate": 0.10, "copay": 20},
            "PPO":  {"deductible": 1500, "coinsurance_rate": 0.15, "copay": 30},
            "EPO":  {"deductible": 2000, "coinsurance_rate": 0.20, "copay": 40},
            "POS":  {"deductible": 1200, "coinsurance_rate": 0.12, "copay": 25},
            "HDHP": {"deductible": 3500, "coinsurance_rate": 0.05, "copay": 0}
        }

        params = plan_params[plan_type]
        annual_deductible = params["deductible"]
        coinsurance_rate = params["coinsurance_rate"]
        copay = params["copay"]

        # Simulate service code lookup (simplified)
        # In real scenario, this would call a medical code database
        service_codes_db = {
            "99213": {"name": "Office Visit - Level 3", "category": "evaluation"},
            "J1100": {"name": "Dexamethasone Injection", "category": "medication"},
            "93000": {"name": "ECG (Electrocardiogram)", "category": "diagnostic"},
            "85025": {"name": "Complete Blood Count (CBC)", "category": "lab"}
        }

        service_info = service_codes_db.get(service_code, {"name": "Unknown Service", "category": "other"})

        # Check if service is covered (simplified - assume all codes are covered)
        # Determine remaining deductible
        remaining_deductible = max(0, annual_deductible - deductible_met)
        deductible_applied = min(remaining_deductible, service_cost)
        cost_after_deductible = service_cost - deductible_applied

        # Calculate patient responsibility
        # Copay applies first if service is office visit
        if service_info["category"] == "evaluation" and plan_type != "HDHP":
            patient_copay = min(copay, cost_after_deductible)
        else:
            patient_copay = 0

        # Calculate coinsurance on remaining amount after copay
        remaining_after_copay = cost_after_deductible - patient_copay
        coinsurance_amount = remaining_after_copay * coinsurance_rate
        patient_coinsurance = round(coinsurance_amount, 2)

        patient_responsibility = round(deductible_applied + patient_copay + patient_coinsurance, 2)
        insurance_payout = round(service_cost - patient_responsibility, 2)

        # Determine approval status
        # Simple rules for demonstration:
        is_approved = True
        denial_reason = None

        # Rule 1: Check if service cost exceeds reasonable limit (e.g., $50k for basic procedures)
        if service_cost > 50000 and service_info["category"] != "medication":
            is_approved = False
            denial_reason = "Service cost exceeds reasonable limit for this procedure type. Requires prior authorization."

        # Rule 2: Check if patient's total deductible is way beyond met (indicates possible fraud)
        if deductible_met > annual_deductible * 2:
            is_approved = False
            denial_reason = "Deductible amount claimed exceeds plan maximum. Possible data inconsistency."

        # Rule 3: Check date - cannot be in the future
        service_date = datetime.strptime(date_of_service, "%Y-%m-%d")
        if service_date > datetime.now():
            is_approved = False
            denial_reason = "Date of service cannot be in the future."

        # Build result
        result = {
            "patient_id": patient_id,
            "insurance_plan": insurance_plan,
            "plan_type": plan_type,
            "service_code": service_code,
            "service_name": service_info["name"],
            "service_cost": service_cost,
            "date_of_service": date_of_service,
            "deductible_applied": round(deductible_applied, 2),
            "remaining_deductible": round(max(0, annual_deductible - deductible_met), 2),
            "copay_applied": round(patient_copay, 2),
            "coinsurance_applied": patient_coinsurance,
            "patient_responsibility": patient_responsibility,
            "insurance_payout": insurance_payout,
            "status": "approved" if is_approved else "denied",
        }

        if not is_approved:
            result["denial_reason"] = denial_reason

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error processing claim: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "insurance_claim_processor",
    "description": "Process a healthcare insurance claim by validating patient coverage, calculating patient responsibility versus insurance payout, and determining if the claim should be approved or denied based on policy rules and service codes.",
    "category": "operations",
    "domain": "healthcare",
    "risk_level": "medium",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., medical record number or insurance member ID).",
            "examples": [
                "PTN-10042",
                "MEMBER-8823"
            ]
        },
        "insurance_plan": {
            "type": "string",
            "description": "Name of the insurance plan covering the patient.",
            "examples": [
                "BlueCross Standard",
                "Aetna Premium",
                "Medicare Part B"
            ]
        },
        "service_code": {
            "type": "string",
            "description": "Medical service billing code (CPT or HCPCS code) for the procedure or service.",
            "examples": [
                "99213",
                "J1100",
                "93000"
            ]
        },
        "service_cost": {
            "type": "number",
            "description": "Total cost of the medical service in USD before insurance adjustments.",
            "minimum": 0
        },
        "date_of_service": {
            "type": "string",
            "description": "Date when the medical service was provided, in YYYY-MM-DD format.",
            "examples": [
                "2025-02-15"
            ]
        },
        "deductible_met": {
            "type": "number",
            "description": "Optional: Amount of the annual deductible already met by the patient prior to this claim. Defaults to 0 if not provided.",
            "minimum": 0
        },
        "plan_type": {
            "type": "string",
            "description": "Optional: Type of insurance plan, which affects co-pay and co-insurance calculations.",
            "enum": [
                "HMO",
                "PPO",
                "EPO",
                "POS",
                "HDHP"
            ],
            "default": "PPO"
        }
    },
    "required": [
        "patient_id",
        "insurance_plan",
        "service_code",
        "service_cost",
        "date_of_service"
    ]
},
}
