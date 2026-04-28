"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Schedule, reschedule, or cancel patient appointments in healthcare."""
    import json
    from datetime import datetime
    import uuid

    try:
        data = json.loads(payload)
        action = data.get('action')
        patient_id = data.get('patient_id')
        provider_id = data.get('provider_id')
        appointment_date = data.get('appointment_date')
        appointment_time = data.get('appointment_time')
        appointment_type = data.get('appointment_type')
        reason = data.get('reason', '')
        appointment_id = data.get('appointment_id')
        patient_contact = data.get('patient_contact')

        # Validate required fields
        if not all([action, patient_id, provider_id, appointment_date, appointment_time, appointment_type]):
            return json.dumps({'error': 'Missing required fields: action, patient_id, provider_id, appointment_date, appointment_time, appointment_type'})

        # Validate date format
        try:
            datetime.strptime(appointment_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format, expected YYYY-MM-DD'})

        # Validate time format
        try:
            datetime.strptime(appointment_time, '%H:%M')
        except ValueError:
            return json.dumps({'error': 'Invalid time format, expected HH:MM'})

        # Simulate appointment management logic
        provider_names = {
            'P001': 'Dr. Sarah Johnson',
            'P002': 'Dr. Michael Chen',
            'P003': 'Nurse Practitioner Emily Davis',
            'P004': 'Dr. Robert Patel'
        }
        provider_name = provider_names.get(provider_id, provider_id)

        if action == 'schedule':
            # Generate a new appointment ID
            new_appointment_id = f'A{str(uuid.uuid4())[:8].upper()}'
            result = {
                'status': 'scheduled',
                'appointment_id': new_appointment_id,
                'patient_id': patient_id,
                'provider_name': provider_name,
                'appointment_date': appointment_date,
                'appointment_time': appointment_time,
                'appointment_type': appointment_type,
                'reason': reason,
                'patient_contact': patient_contact if patient_contact else None
            }

        elif action == 'reschedule':
            if not appointment_id:
                return json.dumps({'error': 'appointment_id is required for reschedule action'})
            # Update appointment details
            result = {
                'status': 'rescheduled',
                'appointment_id': appointment_id,
                'patient_id': patient_id,
                'provider_name': provider_name,
                'previous_date': '2025-02-10',
                'previous_time': '10:00',
                'new_date': appointment_date,
                'new_time': appointment_time,
                'appointment_type': appointment_type,
                'reason': reason
            }

        elif action == 'cancel':
            if not appointment_id:
                return json.dumps({'error': 'appointment_id is required for cancel action'})
            # Generate cancellation record
            result = {
                'status': 'cancelled',
                'appointment_id': appointment_id,
                'patient_id': patient_id,
                'provider_name': provider_name,
                'cancelled_date': appointment_date,
                'cancelled_time': appointment_time,
                'reason': reason if reason else 'No reason provided'
            }

        else:
            return json.dumps({'error': 'Invalid action. Must be schedule, reschedule, or cancel'})

        # Add timestamp
        result['timestamp'] = datetime.now().isoformat()

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "patient_appointment_scheduler",
    "description": "Schedule, reschedule, or cancel a patient appointment in a healthcare system, returning the appointment confirmation details including appointment ID, date, time, and provider name for use in patient records and calendar management.",
    "category": "operations",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The operation to perform: schedule, reschedule, or cancel",
            "enum": [
                "schedule",
                "reschedule",
                "cancel"
            ]
        },
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., medical record number)"
        },
        "provider_id": {
            "type": "string",
            "description": "Unique identifier for the healthcare provider (e.g., doctor or nurse practitioner)"
        },
        "appointment_date": {
            "type": "string",
            "description": "Date of the appointment in YYYY-MM-DD format",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
        },
        "appointment_time": {
            "type": "string",
            "description": "Time of the appointment in HH:MM format (24-hour)",
            "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"
        },
        "appointment_type": {
            "type": "string",
            "description": "Type of medical appointment",
            "enum": [
                "consultation",
                "follow-up",
                "check-up",
                "emergency",
                "procedure",
                "telehealth"
            ]
        },
        "reason": {
            "type": "string",
            "description": "Optional: Reason for the appointment (brief description of symptoms or purpose)"
        },
        "appointment_id": {
            "type": "string",
            "description": "Optional: Existing appointment ID required for reschedule or cancel actions"
        },
        "patient_contact": {
            "type": "string",
            "description": "Optional: Patient phone number or email for appointment reminders"
        }
    },
    "required": [
        "action",
        "patient_id",
        "provider_id",
        "appointment_date",
        "appointment_time",
        "appointment_type"
    ]
},
}
