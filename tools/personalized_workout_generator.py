"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a personalized workout plan based on user profile."""
    import json
    import random

    try:
        data = json.loads(payload)
        fitness_level = data.get('fitness_level')
        goal = data.get('goal')
        equipment = data.get('available_equipment', [])
        days_per_week = data.get('days_per_week')
        duration = data.get('session_duration_minutes')

        # Validate required fields
        if not all([fitness_level, goal, equipment, days_per_week, duration]):
            return json.dumps({'error': 'Missing required fields'})

        # Define exercise database by category
        bodyweight_exercises = {
            'push': ['push_ups', 'diamond_push_ups', 'decline_push_ups', 'pike_push_ups'],
            'pull': ['pull_ups', 'chin_ups', 'inverted_rows', 'bodyweight_rows'],
            'legs': ['squats', 'lunges', 'bulgarian_split_squats', 'glute_bridges', 'calf_raises'],
            'core': ['planks', 'crunches', 'russian_twists', 'leg_raises', 'mountain_climbers']
        }

        weighted_exercises = {
            'push': ['bench_press', 'incline_press', 'overhead_press', 'dumbbell_flyes', 'tricep_extensions'],
            'pull': ['barbell_rows', 'lat_pulldowns', 'dumbbell_rows', 'face_pulls', 'bicep_curls'],
            'legs': ['barbell_squats', 'deadlifts', 'leg_press', 'hamstring_curls', 'leg_extensions'],
            'core': ['weighted_crunches', 'cable_rotations', 'hanging_leg_raises', 'ab_wheel_rollouts']
        }

        # Determine exercise selection based on equipment
        has_weights = any(eq in ['dumbbells', 'barbell', 'kettlebell', 'cable_machine', 'machine_weights'] for eq in equipment)
        source_exercises = weighted_exercises if has_weights else bodyweight_exercises

        # Determine sets and reps based on goal and level
        if goal == 'strength':
            rep_range = (3, 6)
            set_range = (4, 6)
            rest_seconds = 180
        elif goal == 'hypertrophy':
            rep_range = (8, 12)
            set_range = (3, 5)
            rest_seconds = 90
        elif goal == 'endurance':
            rep_range = (15, 20)
            set_range = (2, 4)
            rest_seconds = 45
        else:  # fat_loss or general
            rep_range = (10, 15)
            set_range = (3, 4)
            rest_seconds = 60

        if fitness_level == 'beginner':
            rep_range = (rep_range[0], rep_range[1] - 2)
            set_range = (set_range[0], set_range[1] - 1)
        elif fitness_level == 'advanced':
            rep_range = (rep_range[0] + 2, rep_range[1] + 4)
            set_range = (set_range[0] + 1, set_range[1] + 1)

        # Calculate exercises per session based on duration
        exercises_per_session = max(3, min(8, duration // 10))

        # Generate weekly plan
        weekly_plan = []
        muscle_groups = ['push', 'pull', 'legs', 'core']
        
        for day in range(days_per_week):
            primary_group = muscle_groups[day % len(muscle_groups)]
            secondary_group = muscle_groups[(day + 1) % len(muscle_groups)]
            
            session_exercises = []
            available_exercise_pool = source_exercises.get(primary_group, []) + source_exercises.get(secondary_group, [])
            
            for i in range(min(exercises_per_session, len(available_exercise_pool))):
                exercise_name = random.choice(available_exercise_pool)
                available_exercise_pool.remove(exercise_name)
                
                reps = random.randint(rep_range[0], rep_range[1])
                sets = random.randint(set_range[0], set_range[1])
                
                session_exercises.append({
                    'name': exercise_name.replace('_', ' ').title(),
                    'sets': sets,
                    'reps': reps,
                    'rest_seconds': rest_seconds
                })

            weekly_plan.append({
                'day': day + 1,
                'focus': f"{primary_group.title()} / {secondary_group.title()}",
                'exercises': session_exercises,
                'estimated_duration_minutes': sum(e['sets'] * e['reps'] * 5 + e['rest_seconds'] // 60 for e in session_exercises)
            })

        result = {
            'plan': weekly_plan,
            'summary': {
                'fitness_level': fitness_level,
                'goal': goal,
                'days_per_week': days_per_week,
                'session_duration_target': duration,
                'total_weekly_exercises': sum(len(day['exercises']) for day in weekly_plan),
                'equipment_needed': equipment
            }
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "personalized_workout_generator",
    "description": "Generate a personalized workout plan based on user profile including fitness level, goals, available equipment, and preferred workout duration, returning a structured daily/weekly exercise regimen with sets, reps, and rest periods.",
    "category": "generate",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "fitness_level": {
            "type": "string",
            "description": "User's current fitness level",
            "enum": [
                "beginner",
                "intermediate",
                "advanced"
            ]
        },
        "goal": {
            "type": "string",
            "description": "Primary fitness goal",
            "enum": [
                "strength",
                "hypertrophy",
                "endurance",
                "fat_loss",
                "general_fitness"
            ]
        },
        "available_equipment": {
            "type": "array",
            "description": "List of equipment available to the user",
            "items": {
                "type": "string",
                "enum": [
                    "bodyweight",
                    "dumbbells",
                    "barbell",
                    "kettlebell",
                    "resistance_bands",
                    "cable_machine",
                    "machine_weights",
                    "pull_up_bar",
                    "bench",
                    "cardio_machine"
                ]
            }
        },
        "days_per_week": {
            "type": "integer",
            "description": "Number of training days per week",
            "minimum": 1,
            "maximum": 7
        },
        "session_duration_minutes": {
            "type": "integer",
            "description": "Desired duration of each workout session in minutes",
            "minimum": 15,
            "maximum": 120
        },
        "gender": {
            "type": "string",
            "description": "Optional: User's gender for personalized recommendations",
            "enum": [
                "male",
                "female",
                "other"
            ]
        },
        "age": {
            "type": "integer",
            "description": "Optional: User's age for age-appropriate exercise selection",
            "minimum": 10,
            "maximum": 100
        }
    },
    "required": [
        "fitness_level",
        "goal",
        "available_equipment",
        "days_per_week",
        "session_duration_minutes"
    ]
},
}
