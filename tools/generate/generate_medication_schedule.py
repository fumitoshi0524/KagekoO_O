"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a daily medication schedule for a patient."""
    import json
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        
        # Validate required fields
        if 'patient_id' not in data:
            return json.dumps({'error': 'patient_id is required'}, ensure_ascii=False)
        if 'medications' not in data or not data['medications']:
            return json.dumps({'error': 'At least one medication is required'}, ensure_ascii=False)
        if 'meal_times' not in data:
            return json.dumps({'error': 'meal_times is required'}, ensure_ascii=False)
            
        meal_times = data['meal_times']
        required_meals = ['breakfast', 'lunch', 'dinner']
        for meal in required_meals:
            if meal not in meal_times:
                return json.dumps({'error': f'{meal} time is required'}, ensure_ascii=False)
            
        # Parse meal times
        try:
            breakfast = datetime.strptime(meal_times['breakfast'], '%H:%M')
            lunch = datetime.strptime(meal_times['lunch'], '%H:%M')
            dinner = datetime.strptime(meal_times['dinner'], '%H:%M')
        except ValueError:
            return json.dumps({'error': 'Invalid time format. Use HH:MM 24-hour format.'}, ensure_ascii=False)
        
        # Sort meal times to determine intervals
        meals = [('breakfast', breakfast), ('lunch', lunch), ('dinner', dinner)]
        meals.sort(key=lambda x: x[1])
        
        # Generate schedule for each medication
        schedule = []
        for med in data['medications']:
            med_name = med.get('medication_name', 'Unknown Medication')
            dosage = med.get('dosage', '')
            frequency = med.get('frequency', 1)
            with_food = med.get('with_food', False)
            special = med.get('special_instructions', '')
            
            if frequency <= 0 or frequency > 6:
                return json.dumps({'error': 'Frequency must be between 1 and 6 times per day'}, ensure_ascii=False)
            
            # Distribute doses throughout the day based on meal times
            if frequency == 1:
                # Take with first meal or morning
                admin_times = [meals[0][1]]
            elif frequency == 2:
                # Take with breakfast and dinner
                admin_times = [meals[0][1], meals[2][1]]
            elif frequency == 3:
                # Take with each meal
                admin_times = [m[1] for m in meals]
            elif frequency == 4:
                # Take with meals and bedtime (8pm)
                admin_times = [m[1] for m in meals] + [datetime.strptime('20:00', '%H:%M')]
            elif frequency == 5:
                # Take with meals, mid-morning, and bedtime
                mid_morning = meals[0][1] + timedelta(hours=3)
                admin_times = [meals[0][1], mid_morning, meals[1][1], meals[2][1], datetime.strptime('20:00', '%H:%M')]
            else:  # 6 times per day
                # Every 4 hours starting from breakfast
                admin_times = []
                current = meals[0][1]
                for _ in range(6):
                    admin_times.append(current)
                    current += timedelta(hours=4)
            
            # Format admin times as strings
            time_strings = [t.strftime('%H:%M') for t in sorted(admin_times)]
            
            # Add to schedule
            entry = {
                'medication_name': med_name,
                'dosage': dosage,
                'frequency': frequency,
                'administration_times': time_strings,
                'with_food': with_food,
                'special_instructions': special
            }
            schedule.append(entry)
        
        # Build result
        result = {
            'patient_id': data['patient_id'],
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'schedule': schedule,
            'total_medications': len(schedule),
            'meal_times': {
                'breakfast': meal_times['breakfast'],
                'lunch': meal_times['lunch'],
                'dinner': meal_times['dinner']
            }
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_medication_schedule",
    "description": "Generate a daily medication schedule for a patient based on their prescribed medications, dosage instructions, and typical meal times, returning a structured timeline with medication names, dosages, and administration times.",
    "category": "generate",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_id": {
            "type": "string",
            "description": "Unique identifier for the patient (e.g., medical record number)"
        },
        "medications": {
            "type": "array",
            "description": "List of medications with prescription details",
            "items": {
                "type": "object",
                "properties": {
                    "medication_name": {
                        "type": "string",
                        "description": "Generic or brand name of the medication"
                    },
                    "dosage": {
                        "type": "string",
                        "description": "Dosage strength and form (e.g., 500mg, 1 tablet)"
                    },
                    "frequency": {
                        "type": "integer",
                        "description": "Number of times per day the medication should be taken"
                    },
                    "with_food": {
                        "type": "boolean",
                        "description": "Whether the medication should be taken with food"
                    },
                    "special_instructions": {
                        "type": "string",
                        "description": "Optional: Any special instructions (e.g., take before breakfast)"
                    }
                },
                "required": [
                    "medication_name",
                    "dosage",
                    "frequency"
                ]
            }
        },
        "meal_times": {
            "type": "object",
            "properties": {
                "breakfast": {
                    "type": "string",
                    "description": "Usual breakfast time (24-hour format, e.g., '07:00')",
                    "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"
                },
                "lunch": {
                    "type": "string",
                    "description": "Usual lunch time (24-hour format, e.g., '12:00')",
                    "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"
                },
                "dinner": {
                    "type": "string",
                    "description": "Usual dinner time (24-hour format, e.g., '18:00')",
                    "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"
                }
            },
            "required": [
                "breakfast",
                "lunch",
                "dinner"
            ]
        }
    },
    "required": [
        "patient_id",
        "medications",
        "meal_times"
    ]
},
}
