"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generates a structured weekly workout routine."""
    import json
    import random
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ['fitness_level', 'goal', 'days_per_week', 'available_equipment']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required field: {field}'}, ensure_ascii=False)
        
        fitness_level = data['fitness_level']
        goal = data['goal']
        days_per_week = int(data['days_per_week'])
        available_equipment = data['available_equipment']
        session_duration = data.get('session_duration_minutes', 45)
        focus_areas = data.get('focus_areas', [])
        
        # Validate ranges
        if days_per_week < 1 or days_per_week > 7:
            return json.dumps({'error': 'days_per_week must be between 1 and 7'}, ensure_ascii=False)
        if session_duration < 15 or session_duration > 180:
            return json.dumps({'error': 'session_duration_minutes must be between 15 and 180'}, ensure_ascii=False)
        
        # Exercise database (exercise, muscle_group, sets, reps)
        exercises = {
            'bodyweight_only': [
                ('Push-ups', 'chest', 3, '10-15'),
                ('Bodyweight Squats', 'legs', 3, '15-20'),
                ('Plank', 'core', 3, '30-60s'),
                ('Lunges', 'legs', 3, '10-12 per leg'),
                ('Diamond Push-ups', 'chest', 3, '8-12'),
                ('Glute Bridges', 'legs', 3, '12-15'),
                ('Mountain Climbers', 'core', 3, '30-45s'),
                ('Burpees', 'full_body', 3, '8-12'),
                ('Tricep Dips (chair)', 'arms', 3, '10-15'),
                ('Bicycle Crunches', 'core', 3, '15-20 per side')
            ],
            'dumbbell': [
                ('Dumbbell Bench Press', 'chest', 4, '8-12'),
                ('Dumbbell Rows', 'back', 4, '10-15'),
                ('Dumbbell Shoulder Press', 'shoulders', 4, '8-12'),
                ('Dumbbell Bicep Curls', 'arms', 3, '10-15'),
                ('Dumbbell Tricep Extensions', 'arms', 3, '10-12'),
                ('Goblet Squats', 'legs', 4, '10-15'),
                ('Dumbbell Lunges', 'legs', 3, '10-12 per leg'),
                ('Dumbbell Deadlifts', 'legs', 4, '8-12'),
                ('Dumbbell Lateral Raises', 'shoulders', 3, '12-15'),
                ('Russian Twists (with weight)', 'core', 3, '12-15 per side')
            ],
            'barbell': [
                ('Barbell Bench Press', 'chest', 4, '6-10'),
                ('Barbell Rows', 'back', 4, '8-12'),
                ('Barbell Overhead Press', 'shoulders', 4, '6-10'),
                ('Barbell Squats', 'legs', 4, '6-10'),
                ('Barbell Deadlifts', 'legs', 4, '5-8'),
                ('Barbell Hip Thrusts', 'legs', 3, '8-12'),
                ('Barbell Bicep Curls', 'arms', 3, '8-12'),
                ('Barbell Shrugs', 'shoulders', 3, '10-15'),
                ('Good Mornings', 'legs', 3, '8-12'),
                ('Barbell Rollouts', 'core', 3, '8-12')
            ]
        }
        
        # Add equipment-specific exercises based on available equipment
        routine_exercises = []
        for eq in available_equipment:
            if eq in exercises:
                routine_exercises.extend(exercises[eq])
        
        if not routine_exercises:
            routine_exercises = exercises['bodyweight_only']
        
        # Map goal to rep ranges and set schemes
        goal_config = {
            'strength': {'sets': '4-6', 'reps': '3-8', 'rest': '3-5 min', 'intensity': 'heavy'},
            'hypertrophy': {'sets': '3-4', 'reps': '8-15', 'rest': '60-90s', 'intensity': 'moderate'},
            'endurance': {'sets': '2-3', 'reps': '15-25', 'rest': '30-60s', 'intensity': 'light'},
            'weight_loss': {'sets': '3-4', 'reps': '12-20', 'rest': '30-45s', 'intensity': 'moderate-high'},
            'general_fitness': {'sets': '3', 'reps': '10-15', 'rest': '60-90s', 'intensity': 'moderate'}
        }
        
        # Adjust exercise selection based on focus areas
        if focus_areas:
            focus_exercises = [e for e in routine_exercises if e[1] in focus_areas]
            if len(focus_exercises) >= 4:
                routine_exercises = focus_exercises + [e for e in routine_exercises if e not in focus_exercises][:6]
        
        # Shuffle and create weekly plan
        random.shuffle(routine_exercises)
        exercises_per_day = max(4, min(8, session_duration // 8))
        
        # Determine split type based on days
        if days_per_week <= 3:
            split_type = 'full_body'
        elif days_per_week <= 5:
            split_type = 'upper_lower'
        else:
            split_type = 'push_pull_legs'
        
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly_routine = []
        
        for day_idx in range(days_per_week):
            day_name = days_of_week[day_idx]
            day_exercises = []
            
            # Select exercises for this day based on split
            if split_type == 'full_body':
                eligible = [e for e in routine_exercises if e[1] != 'core']
                core_eligible = [e for e in routine_exercises if e[1] == 'core']
                if len(eligible) >= exercises_per_day - 1:
                    selected = random.sample(eligible, min(exercises_per_day - 1, len(eligible)))
                else:
                    selected = eligible[:]
                if core_eligible and len(selected) < exercises_per_day:
                    selected.append(random.choice(core_eligible))
            elif split_type == 'upper_lower':
                upper_muscles = ['chest', 'back', 'shoulders', 'arms']
                lower_muscles = ['legs', 'core']
                if day_idx % 2 == 0:  # Upper day
                    eligible = [e for e in routine_exercises if e[1] in upper_muscles]
                else:  # Lower day
                    eligible = [e for e in routine_exercises if e[1] in lower_muscles]
                if len(eligible) >= exercises_per_day:
                    selected = random.sample(eligible, exercises_per_day)
                else:
                    selected = eligible[:] + random.sample([e for e in routine_exercises if e not in selected], max(0, exercises_per_day - len(eligible)))
            else:  # push_pull_legs
                push_muscles = ['chest', 'shoulders', 'arms']
                pull_muscles = ['back', 'arms']
                leg_muscles = ['legs', 'core']
                cycle = [push_muscles, pull_muscles, leg_muscles]
                current_muscles = cycle[day_idx % 3]
                eligible = [e for e in routine_exercises if e[1] in current_muscles]
                if len(eligible) >= exercises_per_day:
                    selected = random.sample(eligible, exercises_per_day)
                else:
                    selected = eligible[:] + random.sample([e for e in routine_exercises if e not in selected], max(0, exercises_per_day - len(eligible)))
            
            # Build exercise objects for this day
            for i, (ex_name, muscle, default_sets, default_reps) in enumerate(selected[:exercises_per_day]):
                # Adjust sets/reps based on goal
                g = goal_config[goal]
                if goal == 'strength':
                    sets_val = random.choice([4, 5, 6])
                    reps_val = random.choice([3, 4, 5, 6])
                elif goal == 'hypertrophy':
                    sets_val = random.choice([3, 4])
                    reps_val = f'{random.choice([8, 10, 12])}-{random.choice([12, 15])}'
                elif goal == 'endurance':
                    sets_val = random.choice([2, 3])
                    reps_val = f'{random.choice([15, 18, 20])}-{random.choice([20, 25])}'
                elif goal == 'weight_loss':
                    sets_val = random.choice([3, 4])
                    reps_val = f'{random.choice([12, 15])}-{random.choice([15, 20])}'
                else:
                    sets_val = 3
                    reps_val = f'{random.choice([10, 12])}-{random.choice([12, 15])}'
                
                day_exercises.append({
                    'name': ex_name,
                    'sets': sets_val,
                    'reps': reps_val,
                    'rest': g['rest'],
                    'muscle_group': muscle
                })
            
            weekly_routine.append({
                'day': day_name,
                'focus': split_type if days_per_week <= 3 else (['Upper Body', 'Lower Body'][day_idx % 2] if split_type == 'upper_lower' else ['Push', 'Pull', 'Legs'][day_idx % 3]),
                'exercises': day_exercises
            })
        
        # Scramble the day order for randomness but keep the correct number of days
        random.shuffle(weekly_routine)
        # Reassign day names in order
        for i, day_routine in enumerate(weekly_routine):
            day_routine['day'] = days_of_week[i]
        
        result = {
            'workout_routine': {
                'fitness_level': fitness_level,
                'goal': goal,
                'days_per_week': days_per_week,
                'session_duration': f'{session_duration} minutes',
                'split_type': split_type.replace('_', ' ').title(),
                'weekly_plan': weekly_routine,
                'recommendations': {
                    'warmup': '5-10 minutes light cardio + dynamic stretching',
                    'cooldown': '5 minutes static stretching',
                    'hydration': 'Drink water throughout workout',
                    'progression': 'Gradually increase weight or reps each week'
                }
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_workout_routine",
    "description": "Generates a structured weekly workout routine based on user's fitness level, primary goal, and available equipment, returning a day-by-day plan with exercise names, sets, reps, and rest periods.",
    "category": "generate",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "fitness_level": {
            "type": "string",
            "description": "User's current fitness experience level",
            "enum": [
                "beginner",
                "intermediate",
                "advanced"
            ]
        },
        "goal": {
            "type": "string",
            "description": "Primary fitness objective for the routine",
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
            "description": "Number of training days per week (between 1 and 7)",
            "minimum": 1,
            "maximum": 7
        },
        "available_equipment": {
            "type": "array",
            "description": "List of equipment the user has access to",
            "items": {
                "type": "string",
                "enum": [
                    "barbell",
                    "dumbbell",
                    "kettlebell",
                    "resistance_bands",
                    "pull_up_bar",
                    "bench",
                    "squat_rack",
                    "cable_machine",
                    "bodyweight_only"
                ]
            }
        },
        "session_duration_minutes": {
            "type": "integer",
            "description": "Optional: Desired workout session length in minutes (default is 45)",
            "default": 45,
            "minimum": 15,
            "maximum": 180
        },
        "focus_areas": {
            "type": "array",
            "description": "Optional: Specific muscle groups or areas to emphasize",
            "items": {
                "type": "string",
                "enum": [
                    "chest",
                    "back",
                    "shoulders",
                    "legs",
                    "arms",
                    "core",
                    "full_body"
                ]
            }
        }
    },
    "required": [
        "fitness_level",
        "goal",
        "days_per_week",
        "available_equipment"
    ]
},
}
