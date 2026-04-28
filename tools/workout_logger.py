"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    try:
        data = json.loads(payload)
        required = ['workout_date', 'exercises', 'duration_minutes']
        for key in required:
            if key not in data:
                return f'error: missing required field {key}'
        exercises = data['exercises']
        if not exercises:
            return 'error: exercises list cannot be empty'
        total_volume = 0
        total_calories = 0
        exercise_summaries = []
        for ex in exercises:
            name = ex['name']
            sets = ex['sets']
            reps = ex['reps']
            weight = ex['weight_kg']
            volume = sets * reps * weight
            total_volume += volume
            exercise_summaries.append({
                'name': name,
                'sets': sets,
                'reps': reps,
                'weight_kg': weight,
                'volume_kg': volume
            })
        user_weight = data.get('user_weight_kg', 70)
        met = 6.0  # moderate resistance training MET
        calories = met * user_weight * (data['duration_minutes'] / 60)
        result = {
            'workout_date': data['workout_date'],
            'duration_minutes': data['duration_minutes'],
            'exercises': exercise_summaries,
            'total_volume_kg': total_volume,
            'estimated_calories_burned': round(calories, 1),
            'summary': {
                'total_exercises': len(exercises),
                'total_sets': sum(e['sets'] for e in exercises),
                'total_reps': sum(e['sets'] * e['reps'] for e in exercises)
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "workout_logger",
    "description": "Log a completed workout session with exercise details, sets, reps, weights, and duration, returning a structured workout summary with total volume and estimated calories burned.",
    "category": "operations",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "workout_date": {
            "type": "string",
            "description": "Date of the workout in YYYY-MM-DD format."
        },
        "exercises": {
            "type": "array",
            "description": "List of exercises performed during the session.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the exercise (e.g., bench press, squat)."
                    },
                    "sets": {
                        "type": "integer",
                        "description": "Number of sets performed.",
                        "minimum": 1
                    },
                    "reps": {
                        "type": "integer",
                        "description": "Number of reps per set.",
                        "minimum": 1
                    },
                    "weight_kg": {
                        "type": "number",
                        "description": "Weight used in kilograms.",
                        "minimum": 0
                    }
                },
                "required": [
                    "name",
                    "sets",
                    "reps",
                    "weight_kg"
                ]
            }
        },
        "duration_minutes": {
            "type": "integer",
            "description": "Total workout duration in minutes.",
            "minimum": 1
        },
        "user_weight_kg": {
            "type": "number",
            "description": "Optional: User's body weight in kilograms for calorie estimation.",
            "minimum": 20
        }
    },
    "required": [
        "workout_date",
        "exercises",
        "duration_minutes"
    ]
},
}
