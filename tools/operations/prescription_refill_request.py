"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json, datetime
    try:
        data = json.loads(payload)
        patient_id = data.get('patient_id')
        medication_id = data.get('medication_id')
        refill_qty = data.get('refill_quantity')
        if not patient_id or not medication_id or refill_qty is None:
            return json.dumps({'error': 'Missing required fields: patient_id, medication_id, refill_quantity'})
        if not isinstance(refill_qty, int) or refill_qty <= 0:
            return json.dumps({'error': 'refill_quantity must be a positive integer'})
        # Simulated validation against hypothetical pharmacy database
        # Replace with actual API calls or DB queries in production
        known_patients = {'patient_123': 'active', 'patient_456': 'inactive'}
        known_medications = {'med_aspirin': {'max_refill': 100, 'refills_left': 3}, 'med_ibuprofen': {'max_refill': 60, 'refills_left': 0}}
        if patient_id not in known_patients or known_patients[patient_id] != 'active':
            return json.dumps({'status': 'rejected', 'reason': 'Patient not active or not found', 'refill_number': None})
        if medication_id not in known_medications:
            return json.dumps({'status': 'rejected', 'reason': 'Medication not found in formulary', 'refill_number': None})
        med = known_medications[medication_id]
        if refill_qty > med['max_refill']:
            return json.dumps({'status': 'rejected', 'reason': f'Refill quantity exceeds maximum allowed ({med["max_refill"]})', 'refill_number': None})
        if med['refills_left'] <= 0:
            return json.dumps({'status': 'rejected', 'reason': 'No refills remaining', 'refill_number': None})
        # Simulate refill processing
        refill_number = f"RX-{patient_id}-{medication_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        return json.dumps({'status': 'approved', 'refill_number': refill_number, 'remaining_refills': med['refills_left'] - 1, 'processed_date': datetime.datetime.now().isoformat()})
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "prescription_refill_request",
    "description": "Process a patient's request to refill an existing prescription by validating the patient ID, medication ID, and refill quantity against pharmacy records, and returning a refill confirmation with a new prescription reference number, or a rejection reason if ineligible.",
    "category": "operations",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient in the healthcare system (e.g., medical record number or patient UUID)."
        },
        "medication_id": {
            "type": "string",
            "description": "Identifier of the medication to be refilled, as recorded in the pharmacy formulary."
        },
        "refill_quantity": {
            "type": "integer",
            "description": "Number of units (e.g., pills, vials) for the refill; must be a positive integer within the allowed range for the prescription."
        },
        "requesting_physician_id": {
            "type": "string",
            "description": "Optional: Identifier of the physician who approved the refill. If omitted, system defaults to the prescriber on file."
        }
    },
    "required": [
        "patient_id",
        "medication_id",
        "refill_quantity"
    ]
},
}
