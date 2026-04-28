"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import random

    try:
        data = json.loads(payload)
        patient_name = data.get('patient_name')
        medications = data.get('medications')
        start_date_str = data.get('start_date')
        duration_days = data.get('duration_days')

        if not patient_name or not medications or not start_date_str or not duration_days:
            return json.dumps({'error': 'Missing required fields'})

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        schedule = []
        time_slots = ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']

        for day_offset in range(duration_days):
            current_date = start_date + timedelta(days=day_offset)
            for med in medications:
                med_name = med['medication_name']
                dosage = med['dosage']
                frequency = med['frequency']
                with_food = med.get('with_food', False)
                special_instructions = med.get('special_instructions', '')
                timing_prefs = med.get('timing_preferences', [])

                # Distribute times across the day
                if timing_prefs:
                    # Map preferences to approximate times
                    pref_to_time = {
                        'breakfast': '07:00',
                        'lunch': '12:00',
                        'dinner': '18:00',
                        'bedtime': '21:00',
                        'morning': '08:00',
                        'afternoon': '14:00',
                        'evening': '20:00'
                    }
                    times = []
                    for pref in timing_prefs[:frequency]:
                        if pref in pref_to_time:
                            times.append(pref_to_time[pref])
                    # Fill remaining if not enough prefs
                    while len(times) < frequency:
                        extra_time = random.choice(time_slots)
                        if extra_time not in times:
                            times.append(extra_time)
                else:
                    # Evenly spread across day
                    step = max(1, len(time_slots) // max(1, frequency))
                    selected_indices = list(range(0, len(time_slots), step))[:frequency]
                    times = [time_slots[i] for i in selected_indices]

                for time in times:
                    entry = {
                        'date': current_date.strftime('%Y-%m-%d'),
                        'time': time,
                        'medication': med_name,
                        'dosage': dosage,
                        'with_food': with_food,
                        'special_instructions': special_instructions
                    }
                    schedule.append(entry)

        # Sort by date then time
        schedule.sort(key=lambda x: (x['date'], x['time']))

        result = {
            'patient_name': patient_name,
            'schedule': schedule,
            'total_reminders': len(schedule),
            'generated_at': datetime.now().isoformat()
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "medication_reminder_generator",
    "description": "Generate a daily medication reminder schedule for a patient based on their prescribed medications, dosages, and timing preferences. Returns a structured schedule with medication names, dosages, times, and special instructions.",
    "category": "generate",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_name": {
            "type": "string",
            "description": "Full name of the patient for whom the schedule is generated."
        },
        "medications": {
            "type": "array",
            "description": "List of prescribed medications with details.",
            "items": {
                "type": "object",
                "properties": {
                    "medication_name": {
                        "type": "string",
                        "description": "Name of the medication (generic or brand)."
                    },
                    "dosage": {
                        "type": "string",
                        "description": "Dosage per intake, e.g., '500mg' or '1 tablet'."
                    },
                    "frequency": {
                        "type": "integer",
                        "description": "Number of times the medication should be taken per day (1-6)."
                    },
                    "timing_preferences": {
                        "type": "array",
                        "description": "Optional: Preferred times of day for intake (e.g., 'breakfast', 'bedtime'). If not provided, times are spread evenly.",
                        "items": {
                            "type": "string"
                        }
                    },
                    "with_food": {
                        "type": "boolean",
                        "description": "Optional: Whether the medication should be taken with food. Default false."
                    },
                    "special_instructions": {
                        "type": "string",
                        "description": "Optional: Any additional instructions (e.g., avoid grapefruit juice)."
                    }
                },
                "required": [
                    "medication_name",
                    "dosage",
                    "frequency"
                ]
            }
        },
        "start_date": {
            "type": "string",
            "description": "The start date for the schedule in YYYY-MM-DD format."
        },
        "duration_days": {
            "type": "integer",
            "description": "Number of days the schedule should cover (1-90)."
        }
    },
    "required": [
        "patient_name",
        "medications",
        "start_date",
        "duration_days"
    ]
},
}
