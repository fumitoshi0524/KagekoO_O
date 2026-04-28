"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a personalized workout routine based on user parameters."""
    import json
    try:
        data = json.loads(payload)
        # Validate required inputs
        required = ["fitness_level", "goal", "equipment"]
        for r in required:
            if r not in data:
                return f'error: missing required parameter "{r}"'
        fitness_level = data["fitness_level"]
        goal = data["goal"]
        equipment = data["equipment"]
        days_per_week = data.get("days_per_week", 3)
        session_duration = data.get("session_duration_minutes", 45)
        # Validate enums
        valid_levels = ["beginner", "intermediate", "advanced"]
        valid_goals = ["strength", "endurance", "weight_loss", "flexibility", "general_fitness"]
        valid_equipment = ["bodyweight", "dumbbells", "barbell", "machine", "full_gym"]
        if fitness_level not in valid_levels:
            return f'error: invalid fitness_level "{fitness_level}". Must be one of {valid_levels}'
        if goal not in valid_goals:
            return f'error: invalid goal "{goal}". Must be one of {valid_goals}'
        if equipment not in valid_equipment:
            return f'error: invalid equipment "{equipment}". Must be one of {valid_equipment}'
        days_per_week = max(1, min(7, days_per_week))
        session_duration = max(15, min(120, session_duration))
        # Generate routine logic based on parameters
        # Define exercise pools
        warm_up_exercises = {
            "bodyweight": ["Arm circles", "Leg swings", "Torso twists", "High knees", "Butt kicks"],
            "dumbbells": ["Light dumbbell swings", "Arm circles with light weights", "Torso twists with plate"],
            "barbell": ["Empty bar good mornings", "Bar dislocates", "Hip circles with bar"],
            "machine": ["Treadmill light jog", "Stationary bike light", "Arm circles"],
            "full_gym": ["Foam rolling", "Light cardio", "Dynamic stretches"]
        }
        main_exercises_pool = {
            "strength": {
                "bodyweight": ["Push-ups", "Bodyweight squats", "Lunges", "Plank", "Glute bridges", "Dips (chair)", "Calf raises"],
                "dumbbells": ["Dumbbell bench press", "Dumbbell rows", "Dumbbell shoulder press", "Dumbbell squats", "Dumbbell lunges", "Dumbbell bicep curls", "Dumbbell deadlifts"],
                "barbell": ["Barbell squats", "Barbell deadlifts", "Barbell bench press", "Barbell rows", "Overhead press", "Barbell hip thrusts", "Barbell shrugs"],
                "machine": ["Leg press", "Lat pulldown", "Chest press machine", "Shoulder press machine", "Leg extension", "Leg curl", "Cable rows"],
                "full_gym": ["Barbell squats", "Deadlifts", "Bench press", "Pull-ups", "Dumbbell rows", "Overhead press", "Leg press"]
            },
            "endurance": {
                "bodyweight": ["Jumping jacks", "Burpees", "Mountain climbers", "High knees", "Squat jumps", "Plank jacks", "Skater hops"],
                "dumbbells": ["Dumbbell thrusters", "Dumbbell snatches", "Dumbbell clean and press", "Dumbbell swings", "Dumbbell burpees"],
                "barbell": ["Barbell thrusters", "Barbell complexes", "Barbell front squats with push press"],
                "machine": ["Treadmill intervals", "Rowing machine", "Assault bike", "Elliptical sprints"],
                "full_gym": ["Rowing intervals", "Treadmill sprints", "Burpee pull-ups", "Kettlebell swings", "Box jumps"]
            },
            "weight_loss": {
                "bodyweight": ["Burpees", "High knees", "Mountain climbers", "Jumping lunges", "Squat jumps", "Plank with shoulder taps", "Bicycle crunches"],
                "dumbbells": ["Dumbbell clean and press", "Dumbbell thrusters", "Dumbbell snatches", "Dumbbell swings", "Dumbbell burpees"],
                "barbell": ["Barbell complexes", "Barbell thrusters", "Barbell snatches"],
                "machine": ["HIIT on treadmill", "Rowing machine intervals", "Assault bike intervals", "Stair climber"],
                "full_gym": ["Kettlebell swings", "Box jumps", "Burpee pull-ups", "Med ball slams", "Row sprints"]
            },
            "flexibility": {
                "bodyweight": ["Downward dog", "Cat-cow stretches", "Standing hamstring stretch", "Quad stretch", "Chest opener", "Spinal twists", "Butterfly stretch"],
                "dumbbells": ["Overhead triceps stretch with dumbbell", "Chest stretch with dumbbell", "Weighted hamstring stretch"],
                "barbell": ["Bar-assisted hamstring stretch", "Bar shoulder stretch"],
                "machine": ["Assisted stretching using cables", "Pilates reformer stretching"],
                "full_gym": ["Yoga poses with blocks", "Stretching using cable machine", "Partner stretches"]
            },
            "general_fitness": {
                "bodyweight": ["Push-ups", "Bodyweight squats", "Plank", "Lunges", "Burpees", "Glute bridges", "Superman holds"],
                "dumbbells": ["Goblet squats", "Dumbbell bench press", "Dumbbell rows", "Dumbbell shoulder press", "Dumbbell lunges"],
                "barbell": ["Barbell squats", "Barbell bench press", "Barbell rows", "Overhead press", "Barbell deadlifts"],
                "machine": ["Chest press", "Lat pulldown", "Leg press", "Shoulder press", "Leg extension"],
                "full_gym": ["Squats", "Bench press", "Pull-ups", "Deadlifts", "Overhead press", "Leg press"]
            }
        }
        cool_down_exercises = ["Hamstring stretch", "Quad stretch", "Chest stretch", "Triceps stretch", "Cat-cow", "Child's pose", "Shoulder stretch"]
        # Select exercises based on fitness level (adjust sets/reps/volume)
        if fitness_level == "beginner":
            sets_range = (2, 3)
            reps_range = (8, 12)
            num_exercises = 5
            intensity = "low to moderate"
        elif fitness_level == "intermediate":
            sets_range = (3, 4)
            reps_range = (10, 15)
            num_exercises = 6
            intensity = "moderate to high"
        else:  # advanced
            sets_range = (4, 5)
            reps_range = (12, 20) if goal == "endurance" else (6, 10) if goal == "strength" else (10, 15)
            num_exercises = 7
            intensity = "high to very high"
        # Build routine
        import random
        random.seed(sum(ord(c) for c in f"{fitness_level}{goal}{equipment}{days_per_week}{session_duration}"))
        warm_up = random.sample(warm_up_exercises.get(equipment, warm_up_exercises["bodyweight"]), min(3, len(warm_up_exercises.get(equipment, warm_up_exercises["bodyweight"]))))
        main_pool = main_exercises_pool[goal][equipment]
        main = random.sample(main_pool, min(num_exercises, len(main_pool)))
        cool_down = random.sample(cool_down_exercises, 4)
        # Structure output
        result = {
            "routine_name": f"{fitness_level.capitalize()} {goal.replace('_', ' ').title()} Routine ({equipment.replace('_', ' ').title()})",
            "summary": {
                "fitness_level": fitness_level,
                "goal": goal,
                "equipment": equipment,
                "days_per_week": days_per_week,
                "session_duration_minutes": session_duration,
                "intensity": intensity,
                "sets": f"{sets_range[0]}-{sets_range[1]}",
                "reps": f"{reps_range[0]}-{reps_range[1]}"
            },
            "warm_up": warm_up,
            "main_exercises": [{"exercise": ex, "sets": f"{sets_range[0]}-{sets_range[1]}", "reps": f"{reps_range[0]}-{reps_range[1]}"} for ex in main],
            "cool_down": cool_down,
            "recommendation": {
                "rest_between_sets": "60-90 seconds" if goal == "strength" else "30-45 seconds",
                "hydration": "Sip water as needed",
                "form_tip": "Focus on controlled movement and proper form"
            }
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "workout_routine_generator",
    "description": "Generate a personalized workout routine based on fitness level (beginner, intermediate, advanced), goal (strength, endurance, weight_loss, flexibility, general_fitness), and available equipment (bodyweight, dumbbells, barbell, machine, full_gym). Returns a structured routine including warm-up, main exercises with sets/reps, and cool-down.",
    "category": "generate",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "fitness_level": {
            "type": "string",
            "description": "The user's current fitness experience level",
            "enum": [
                "beginner",
                "intermediate",
                "advanced"
            ]
        },
        "goal": {
            "type": "string",
            "description": "Primary training objective for the workout routine",
            "enum": [
                "strength",
                "endurance",
                "weight_loss",
                "flexibility",
                "general_fitness"
            ]
        },
        "equipment": {
            "type": "string",
            "description": "Equipment available for the workout",
            "enum": [
                "bodyweight",
                "dumbbells",
                "barbell",
                "machine",
                "full_gym"
            ]
        },
        "days_per_week": {
            "type": "integer",
            "description": "Optional: Number of training days per week (1-7). Defaults to 3.",
            "minimum": 1,
            "maximum": 7
        },
        "session_duration_minutes": {
            "type": "integer",
            "description": "Optional: Target duration per session in minutes (15-120). Defaults to 45.",
            "minimum": 15,
            "maximum": 120
        }
    },
    "required": [
        "fitness_level",
        "goal",
        "equipment"
    ]
},
}
