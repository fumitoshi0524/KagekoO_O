"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Reschedule an existing patient appointment by updating date/time/provider."""
    import json
    from datetime import datetime, timedelta
    import uuid

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ['appointment_id', 'new_date', 'new_time', 'reason']
        for field in required:
            if field not in data or not data[field]:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)

        appointment_id = data['appointment_id']
        new_date_str = data['new_date']
        new_time_str = data['new_time']
        reason = data['reason']
        new_provider_id = data.get('new_provider_id', None)
        notes = data.get('notes', '')

        # Validate appointment ID format (simple check)
        if not appointment_id.startswith('APPT-'):
            return json.dumps({"error": "Invalid appointment ID format. Must start with 'APPT-'."}, ensure_ascii=False)

        # Validate date format and future date check
        try:
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d')
            if new_date <= datetime.now():
                return json.dumps({"error": "New date must be in the future."}, ensure_ascii=False)
        except ValueError:
            return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."}, ensure_ascii=False)

        # Validate time format and operating hours
        try:
            new_time = datetime.strptime(new_time_str, '%H:%M')
            if new_time.hour < 8 or new_time.hour > 18:
                return json.dumps({"error": "Appointment time must be between 08:00 and 18:00."}, ensure_ascii=False)
        except ValueError:
            return json.dumps({"error": "Invalid time format. Use HH:MM in 24-hour format."}, ensure_ascii=False)

        # Validate reason enum
        valid_reasons = ['patient_request', 'provider_unavailable', 'scheduling_error', 'emergency', 'other']
        if reason not in valid_reasons:
            return json.dumps({"error": f"Invalid reason. Must be one of: {', '.join(valid_reasons)}"}, ensure_ascii=False)

        # Validate optional provider ID if provided
        if new_provider_id and not new_provider_id.startswith('PROV-'):
            return json.dumps({"error": "Invalid provider ID format. Must start with 'PROV-'."}, ensure_ascii=False)

        # Validate notes length
        if len(notes) > 500:
            return json.dumps({"error": "Notes must not exceed 500 characters."}, ensure_ascii=False)

        # Simulate finding the original appointment and performing reschedule
        # In production, this would query a real database
        original_appointment = {
            "appointment_id": appointment_id,
            "patient_id": "PAT-45678",
            "provider_id": "PROV-12345",
            "original_date": "2024-12-10",
            "original_time": "10:30",
            "status": "scheduled"
        }

        # Generate confirmation and updated record
        confirmation_id = str(uuid.uuid4())[:8].upper()
        updated_appointment = {
            "appointment_id": appointment_id,
            "patient_id": original_appointment["patient_id"],
            "provider_id": new_provider_id if new_provider_id else original_appointment["provider_id"],
            "old_date": original_appointment["original_date"],
            "old_time": original_appointment["original_time"],
            "new_date": new_date_str,
            "new_time": new_time_str,
            "reason": reason,
            "status": "rescheduled",
            "confirmation_id": confirmation_id,
            "rescheduled_at": datetime.now().isoformat(),
            "notes": notes
        }

        result = {
            "success": True,
            "message": f"Appointment {appointment_id} rescheduled successfully.",
            "confirmation_id": confirmation_id,
            "updated_appointment": updated_appointment
        }
        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload."}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"}, ensure_ascii=False)



TOOL_SPEC = {
    "name": "patient_appointment_reschedule",
    "description": "Reschedule an existing patient appointment by updating the scheduled date, time, and optionally the assigned healthcare provider, returning the updated appointment record for confirmation and scheduling system synchronization.",
    "category": "operations",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "appointment_id": {
            "type": "string",
            "description": "Unique identifier for the existing appointment to be rescheduled (e.g., 'APPT-2024-12345')."
        },
        "new_date": {
            "type": "string",
            "description": "New appointment date in ISO 8601 format (YYYY-MM-DD). Must be a future date."
        },
        "new_time": {
            "type": "string",
            "description": "New appointment time in 24-hour format (HH:MM). Must be within clinic operating hours (08:00-18:00)."
        },
        "reason": {
            "type": "string",
            "enum": [
                "patient_request",
                "provider_unavailable",
                "scheduling_error",
                "emergency",
                "other"
            ],
            "description": "Reason for rescheduling the appointment."
        },
        "new_provider_id": {
            "type": "string",
            "description": "Optional: Alternative healthcare provider identifier (e.g., 'PROV-78901') if the patient wants to change the assigned provider. If not provided, the original provider will be maintained."
        },
        "notes": {
            "type": "string",
            "description": "Optional: Additional notes or special instructions for the rescheduled appointment (max 500 characters)."
        }
    },
    "required": [
        "appointment_id",
        "new_date",
        "new_time",
        "reason"
    ]
},
}
