"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Process a medication refill request for an existing patient prescription."""
    import json
    from datetime import datetime, timedelta
    import random

    try:
        data = json.loads(payload)
        # Validate required fields
        required = ["patient_id", "prescription_id", "pharmacy_id"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"})

        patient_id = data["patient_id"]
        prescription_id = data["prescription_id"]
        pharmacy_id = data["pharmacy_id"]

        # Simulate checking patient and prescription in a database (mock validation)
        # In a real system, here we would query a database.
        # For demonstration, we assume valid if IDs are non-empty and not special.
        if not patient_id.strip() or not prescription_id.strip() or not pharmacy_id.strip():
            return json.dumps({"error": "One or more IDs are empty."})

        # Simulate refill eligibility: random check, assume 90% success rate
        eligible = random.random() < 0.9
        if not eligible:
            # Provide a mock reason for ineligibility
            reasons = ["Prescription expired", "Refills exhausted", "Patient not active"]
            reason = random.choice(reasons)
            return json.dumps({
                "status": "denied",
                "reason": reason,
                "prescription_id": prescription_id,
                "patient_id": patient_id
            })

        # Determine quantity: use provided or default (random between 30 and 90)
        if "quantity" in data and data["quantity"] is not None:
            quantity = data["quantity"]
            if quantity < 1:
                return json.dumps({"error": "Quantity must be at least 1."})
        else:
            quantity = random.randint(30, 90)

        # Determine pickup date: 1-3 business days from request date (or today)
        request_date_str = data.get("refill_request_date", None)
        if request_date_str:
            try:
                request_date = datetime.strptime(request_date_str, "%Y-%m-%d")
            except ValueError:
                return json.dumps({"error": "Invalid refill_request_date format. Use YYYY-MM-DD."})
        else:
            request_date = datetime.now()

        # Simple business day calculation: skip weekends (but simplified for demo)
        # For demo, add 1-3 days randomly
        days_to_add = random.randint(1, 3)
        pickup_date = request_date + timedelta(days=days_to_add)
        # If it lands on weekend, push to Monday (simplified)
        if pickup_date.weekday() == 5:  # Saturday
            pickup_date += timedelta(days=2)
        elif pickup_date.weekday() == 6:  # Sunday
            pickup_date += timedelta(days=1)

        result = {
            "status": "approved",
            "refill_id": f"REF-{random.randint(10000, 99999)}",
            "patient_id": patient_id,
            "prescription_id": prescription_id,
            "pharmacy_id": pharmacy_id,
            "quantity": quantity,
            "pickup_date": pickup_date.strftime("%Y-%m-%d"),
            "message": f"Refill approved. Estimated pickup date: {pickup_date.strftime('%Y-%m-%d')}."
        }
        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


TOOL_SPEC = {
    "name": "prescription_refill",
    "description": "Process a medication refill request for an existing patient prescription by verifying patient identity, checking refill eligibility, and returning a confirmation with the estimated pick-up date.",
    "category": "operations",
    "domain": "healthcare",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., medical record number, patient UUID)."
        },
        "prescription_id": {
            "type": "string",
            "description": "Unique identifier for the specific prescription to be refilled."
        },
        "pharmacy_id": {
            "type": "string",
            "description": "Identifier of the pharmacy where the refill will be picked up."
        },
        "quantity": {
            "type": "integer",
            "description": "Optional: Number of dosage units requested for the refill (e.g., 30 pills). If omitted, defaults to the original prescription quantity.",
            "minimum": 1
        },
        "refill_request_date": {
            "type": "string",
            "description": "Optional: Date of the refill request in YYYY-MM-DD format. If omitted, current date is used."
        }
    },
    "required": [
        "patient_id",
        "prescription_id",
        "pharmacy_id"
    ]
},
}
