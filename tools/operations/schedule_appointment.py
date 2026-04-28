"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Schedule a new patient appointment with a healthcare provider."""
    import json
    from datetime import datetime, timedelta
    import uuid

    try:
        data = json.loads(payload)

        # Validate required fields
        required_fields = ["patient_id", "provider_id", "appointment_date", "appointment_time", "appointment_type"]
        for field in required_fields:
            if field not in data:
                return f'error: Missing required field: {field}'

        patient_id = data["patient_id"]
        provider_id = data["provider_id"]
        appointment_date = data["appointment_date"]
        appointment_time = data["appointment_time"]
        appointment_type = data["appointment_type"]
        reason = data.get("reason", "")
        notes = data.get("notes", "")
        duration = data.get("duration_minutes", 30)

        # Validate appointment_date format
        try:
            datetime.strptime(appointment_date, "%Y-%m-%d")
        except ValueError:
            return f'error: Invalid date format (expected YYYY-MM-DD): {appointment_date}'

        # Validate appointment_time format
        try:
            datetime.strptime(appointment_time, "%H:%M")
        except ValueError:
            return f'error: Invalid time format (expected HH:MM): {appointment_time}'

        # Validate appointment_type
        valid_types = ["routine", "followup", "consultation", "emergency"]
        if appointment_type not in valid_types:
            return f'error: Invalid appointment type (must be one of {valid_types}): {appointment_type}'

        # Validate duration
        if duration < 15 or duration > 120:
            return f'error: Duration must be between 15 and 120 minutes'

        # Validate that appointment is not in the past
        appointment_datetime_str = f"{appointment_date} {appointment_time}"
        appointment_datetime = datetime.strptime(appointment_datetime_str, "%Y-%m-%d %H:%M")
        if appointment_datetime < datetime.now():
            return f'error: Cannot schedule appointment in the past'

        # Generate appointment ID
        appointment_id = str(uuid.uuid4())[:8].upper()

        # Calculate end time
        start_time = appointment_datetime
        end_time = start_time + timedelta(minutes=duration)

        # Simulate provider lookup (in production, query database)
        provider_name = f"Provider_{provider_id[:6]}"
        provider_specialty = "General Medicine"

        # Simulate patient lookup
        patient_name = f"Patient_{patient_id[:6]}"

        # Build the appointment confirmation
        result = {
            "appointment_id": appointment_id,
            "status": "confirmed",
            "patient": {
                "id": patient_id,
                "name": patient_name
            },
            "provider": {
                "id": provider_id,
                "name": provider_name,
                "specialty": provider_specialty
            },
            "appointment": {
                "date": appointment_date,
                "start_time": appointment_time,
                "end_time": end_time.strftime("%H:%M"),
                "type": appointment_type,
                "duration_minutes": duration,
                "reason": reason
            },
            "notes": notes,
            "created_at": datetime.now().isoformat()
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return f'error: Invalid JSON payload: {payload}'
    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "schedule_appointment",
    "description": "Schedule a new patient appointment with a healthcare provider, returning a confirmation with the appointment ID, date, time, and provider details for use in patient records and calendar management.",
    "category": "operations",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier of the patient making the appointment"
        },
        "provider_id": {
            "type": "string",
            "description": "Unique identifier of the healthcare provider (doctor, nurse practitioner, etc.)"
        },
        "appointment_date": {
            "type": "string",
            "description": "Date of the appointment in YYYY-MM-DD format"
        },
        "appointment_time": {
            "type": "string",
            "description": "Time of the appointment in HH:MM format, using 24-hour clock"
        },
        "appointment_type": {
            "type": "string",
            "enum": [
                "routine",
                "followup",
                "consultation",
                "emergency"
            ],
            "description": "Category of the medical visit"
        },
        "reason": {
            "type": "string",
            "description": "Brief description of the reason for the visit or symptoms"
        },
        "notes": {
            "type": "string",
            "description": "Optional: Additional notes or instructions for the appointment"
        },
        "duration_minutes": {
            "type": "integer",
            "description": "Optional: Duration of the appointment in minutes (default is 30)",
            "minimum": 15,
            "maximum": 120
        }
    },
    "required": [
        "patient_id",
        "provider_id",
        "appointment_date",
        "appointment_time",
        "appointment_type"
    ]
},
}
