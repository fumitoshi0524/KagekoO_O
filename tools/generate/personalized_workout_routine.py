"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a customized weekly workout routine."""
    import json
    import random
    
    try:
        data = json.loads(payload)
        fitness_level = data.get('fitness_level')
        goal = data.get('goal')
        days_per_week = data.get('days_per_week')
        equipment = data.get('equipment')
        duration = data.get('duration_minutes', 45)
        focus_areas = data.get('focus_areas', [])
        
        # Validate required fields
        if not all([fitness_level, goal, days_per_week, equipment]):
            return json.dumps({"error": "Missing required fields: fitness_level, goal, days_per_week, equipment"}, ensure_ascii=False)
        
        valid_levels = ['beginner', 'intermediate', 'advanced']
        valid_goals = ['strength', 'hypertrophy', 'endurance', 'weight_loss', 'general_fitness']
        if fitness_level not in valid_levels:
            return json.dumps({"error": f"Invalid fitness_level. Must be one of {valid_levels}"}, ensure_ascii=False)
        if goal not in valid_goals:
            return json.dumps({"error": f"Invalid goal. Must be one of {valid_goals}"}, ensure_ascii=False)
        if not isinstance(days_per_week, int) or days_per_week < 3 or days_per_week > 6:
            return json.dumps({"error": "days_per_week must be an integer between 3 and 6"}, ensure_ascii=False)
        
        # Equipment difficulty mapping
        equipment_complexity = {
            'bodyweight': 1,
            'resistance_bands': 2,
            'dumbbells': 3,
            'kettlebells': 3,
            'barbell': 4,
            'cable_machine': 4,
            'smith_machine': 4,
            'full_gym': 5
        }
        max_complexity = max(equipment_complexity[e] for e in equipment if e in equipment_complexity)
        
        # Exercise template database
        exercises_by_muscle = {
            'chest': ['push-ups', 'dumbbell bench press', 'incline press', 'cable flyes', 'dips'],
            'back': ['pull-ups', 'bent-over rows', 'lat pulldowns', 'seated cable rows', 'dumbbell rows'],
            'shoulders': ['overhead press', 'lateral raises', 'front raises', 'face pulls', 'reverse flyes'],
            'arms': ['bicep curls', 'tricep pushdowns', 'hammer curls', 'skull crushers', 'chin-ups'],
            'legs': ['squats', 'lunges', 'deadlifts', 'leg press', 'calf raises', 'step-ups'],
            'core': ['planks', 'crunches', 'russian twists', 'leg raises', 'mountain climbers']
        }
        
        # Rep ranges based on goal
        rep_ranges = {
            'strength': (3, 6),
            'hypertrophy': (8, 12),
            'endurance': (15, 25),
            'weight_loss': (12, 20),
            'general_fitness': (10, 15)
        }
        
        # Determine split type
        if days_per_week == 3:
            split = 'full_body'
        elif days_per_week == 4:
            split = 'upper_lower'
        elif days_per_week == 5:
            split = 'push_pull_legs'
        else:
            split = 'push_pull_legs_plus'
        
        # Build weekly schedule
        workout_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][:days_per_week]
        weekly_schedule = []
        
        if split == 'full_body':
            target_muscles = [['chest', 'back', 'shoulders', 'legs', 'core']] * days_per_week
        elif split == 'upper_lower':
            target_muscles = [['chest', 'back', 'shoulders', 'arms'], ['legs', 'core']] * (days_per_week // 2)
            if days_per_week % 2 == 1:
                target_muscles.append(['chest', 'back', 'shoulders', 'legs', 'arms', 'core'])
        elif split == 'push_pull_legs':
            if days_per_week == 5:
                target_muscles = [['chest', 'shoulders'], ['back', 'arms'], ['legs', 'core'], ['chest', 'shoulders', 'arms'], ['back', 'legs']]
            else:
                target_muscles = [['chest', 'shoulders'], ['back', 'arms'], ['legs', 'core'], ['chest', 'shoulders'], ['back', 'arms'], ['legs']]
        else:
            target_muscles = [['chest', 'shoulders'], ['back', 'arms'], ['legs', 'core'], ['chest', 'shoulders', 'arms'], ['back', 'legs'], ['full_body']]
        
        for i, day in enumerate(workout_days):
            day_muscles = target_muscles[i % len(target_muscles)]
            # Apply focus areas if specified
            if focus_areas:
                day_muscles = [m for m in day_muscles if m in focus_areas] or day_muscles
            
            exercises = []
            for muscle in day_muscles[:4]:  # Max 4 muscle groups per session
                available_exercises = exercises_by_muscle.get(muscle, ['bodyweight squats'])
                # Filter by equipment availability
                if 'bodyweight' in equipment:
                    suitable = [e for e in available_exercises if 'dumbbell' not in e and 'barbell' not in e and 'cable' not in e]
                elif 'dumbbells' in equipment:
                    suitable = available_exercises
                elif 'full_gym' in equipment:
                    suitable = available_exercises
                else:
                    suitable = [e for e in available_exercises if len(e) < 20]
                
                if not suitable:
                    suitable = [available_exercises[0]]
                
                chosen = random.choice(suitable)
                min_rep, max_rep = rep_ranges[goal]
                sets = 3 if fitness_level == 'beginner' else (4 if fitness_level == 'intermediate' else 5)
                rest = 90 if goal == 'strength' else (60 if goal in ['hypertrophy', 'general_fitness'] else 30)
                
                exercises.append({
                    'name': chosen.capitalize(),
                    'muscle_group': muscle,
                    'sets': sets,
                    'reps_range': f"{min_rep}-{max_rep}",
                    'rest_seconds': rest,
                    'equipment': random.choice(equipment)
                })
            
            weekly_schedule.append({
                'day': day,
                'workout_type': split.replace('_', ' ').title(),
                'duration_minutes': duration,
                'exercises': exercises
            })
        
        result = {
            'routine_name': f"{fitness_level.capitalize()} {goal.replace('_', ' ').title()} Plan",
            'fitness_level': fitness_level,
            'goal': goal,
            'days_per_week': days_per_week,
            'split_type': split.replace('_', ' ').title(),
            'duration_per_session': duration,
            'weekly_schedule': weekly_schedule
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "personalized_workout_routine",
    "description": "Generate a customized weekly workout routine based on user's fitness level, goals, available equipment, and preferred training days, returning a structured schedule with exercises, sets, reps, and rest periods.",
    "category": "generate",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "fitness_level": {
            "type": "string",
            "description": "Current fitness experience level",
            "enum": [
                "beginner",
                "intermediate",
                "advanced"
            ]
        },
        "goal": {
            "type": "string",
            "description": "Primary training goal",
            "enum": [
                "strength",
                "hypertrophy",
                "endurance",
                "weight_loss",
                "general_fitness"
            ]
        },
        "days_per_week": {
            "type": "integer",
            "description": "Number of training days per week (3-6)",
            "minimum": 3,
            "maximum": 6
        },
        "equipment": {
            "type": "array",
            "description": "Available equipment from the predefined list",
            "items": {
                "type": "string",
                "enum": [
                    "bodyweight",
                    "dumbbells",
                    "barbell",
                    "kettlebells",
                    "resistance_bands",
                    "cable_machine",
                    "smith_machine",
                    "full_gym"
                ]
            },
            "minItems": 1,
            "uniqueItems": True
        },
        "duration_minutes": {
            "type": "integer",
            "description": "Optional: Preferred workout duration per session in minutes (20-90)",
            "minimum": 20,
            "maximum": 90,
            "default": 45
        },
        "focus_areas": {
            "type": "array",
            "description": "Optional: Specific muscle groups to prioritize",
            "items": {
                "type": "string",
                "enum": [
                    "chest",
                    "back",
                    "shoulders",
                    "arms",
                    "legs",
                    "core",
                    "full_body"
                ]
            },
            "uniqueItems": True
        }
    },
    "required": [
        "fitness_level",
        "goal",
        "days_per_week",
        "equipment"
    ]
},
}
