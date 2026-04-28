"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a personalized weekly workout plan based on user fitness goals, available equipment, training frequency, and experience level, returning a structured schedule of exercises with sets, reps, rest times, and progression tips."""
    import json
    import random

    try:
        data = json.loads(payload)
        # Required fields validation
        required = ["goal", "equipment", "days_per_week", "experience_level"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"})

        goal = data["goal"]
        equipment = data["equipment"]
        days = data["days_per_week"]
        level = data["experience_level"]
        duration = data.get("session_duration_minutes", 60)

        # Map goal to rep ranges and volume
        rep_ranges = {
            "strength": (3, 6),
            "hypertrophy": (8, 12),
            "endurance": (15, 20),
            "fat_loss": (12, 15),
            "general_fitness": (10, 15)
        }
        sets_range = {
            "strength": (4, 6),
            "hypertrophy": (3, 4),
            "endurance": (2, 3),
            "fat_loss": (3, 4),
            "general_fitness": (2, 3)
        }

        # Exercise database (simplified but includes compound and isolation exercises)
        all_exercises = {
            "barbell": ["Barbell Bench Press", "Barbell Squat", "Barbell Deadlift", "Barbell Overhead Press", "Barbell Row"],
            "dumbbell": ["Dumbbell Chest Press", "Dumbbell Shoulder Press", "Dumbbell Lunges", "Dumbbell Rows", "Dumbbell Bicep Curls"],
            "kettlebell": ["Kettlebell Swing", "Kettlebell Goblet Squat", "Kettlebell Clean and Press", "Kettlebell Turkish Get-up"],
            "resistance_bands": ["Band Pull-Apart", "Band Squat", "Band Glute Bridge", "Band Rows"],
            "bodyweight": ["Push-ups", "Pull-ups", "Bodyweight Squats", "Planks", "Lunges", "Burpees"],
            "cable_machine": ["Cable Flyes", "Cable Tricep Pushdown", "Cable Face Pulls", "Cable Woodchoppers"],
            "smith_machine": ["Smith Machine Squat", "Smith Machine Bench Press", "Smith Machine Shoulder Press"],
            "cardio_machine": ["Treadmill Running", "Stationary Bike", "Rowing Machine", "Elliptical Trainer"]
        }

        # Filter exercises based on available equipment
        available_exercises = []
        for equip in equipment:
            if equip in all_exercises:
                available_exercises.extend(all_exercises[equip])

        if not available_exercises:
            # Fallback to bodyweight
            available_exercises.extend(all_exercises["bodyweight"])

        # Generate weekly plan
        plan = []
        min_rep, max_rep = rep_ranges[goal]
        min_sets, max_sets = sets_range[goal]

        # Distribute muscle groups across days (simplified upper/lower split for >3 days)
        if days >= 4:
            muscles_per_day = ["Upper Body", "Lower Body", "Upper Body", "Lower Body"]
        elif days == 3:
            muscles_per_day = ["Push", "Pull", "Legs"]
        else:
            muscles_per_day = ["Full Body"] * days

        # Ensure enough days covered
        while len(muscles_per_day) < days:
            muscles_per_day.append("Full Body")

        for day_idx in range(days):
            focus = muscles_per_day[day_idx]
            # Select 4-6 exercises based on focus
            random.shuffle(available_exercises)
            # Choose compound exercises first if possible (prioritize those with body part keywords)
            compound_keywords = ["Bench", "Squat", "Deadlift", "Press", "Row", "Clean", "Swing", "Pull-up", "Lunge"]
            filtered = []
            for ex in available_exercises:
                for kw in compound_keywords:
                    if kw.lower() in ex.lower():
                        filtered.append(ex)
                        break
            if len(filtered) < 4:
                filtered = available_exercises[:]
            # Pick exercises for the day
            n_exercises = min(6, len(filtered))
            if level == "beginner":
                n_exercises = min(4, len(filtered))
            if level == "advanced":
                n_exercises = min(8, len(filtered))

            day_exercises = []
            for i in range(n_exercises):
                ex_name = filtered[i % len(filtered)]
                reps = random.randint(min_rep, max_rep)
                sets = random.randint(min_sets, max_sets)
                rest = "60-90s" if goal in ["hypertrophy", "general_fitness"] else "90-120s" if goal == "strength" else "30-60s"
                day_exercises.append({
                    "exercise": ex_name,
                    "sets": sets,
                    "reps": reps,
                    "rest": rest
                })
            # Estimate time per exercise
            total_time = sum([ex["sets"] * ex["reps"] * 0.6 for ex in day_exercises])  # rough estimate in minutes
            plan.append({
                "day": day_idx + 1,
                "focus": focus,
                "exercises": day_exercises,
                "estimated_duration_minutes": round(total_time)
            })

        # Progression tips based on level
        progression_tips = []
        if level == "beginner":
            progression_tips = ["Start with light weight, focus on form.", "Increase weight by 2.5-5kg once you can complete all reps with good form.", "Rest at least 48 hours between sessions for same muscle groups."]
        elif level == "intermediate":
            progression_tips = ["Use progressive overload: add reps or weight each week.", "Consider deload weeks every 6-8 weeks.", "Incorporate advanced techniques like dropsets or supersets."]
        else:
            progression_tips = ["Periodize your training: mesocycles with varying intensity.", "Track your 1RM and adjust loads accordingly.", "Include periodization blocks for strength, hypertrophy, and peaking."]

        result = {
            "weekly_plan": plan,
            "goal": goal,
            "experience_level": level,
            "equipment_used": equipment,
            "total_days": days,
            "progression_tips": progression_tips,
            "warning": "Consult a healthcare professional before starting any exercise program."
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


TOOL_SPEC = {
    "name": "workout_plan_generator",
    "description": "Generate a personalized weekly workout plan based on user fitness goals, available equipment, training frequency, and experience level, returning a structured schedule of exercises with sets, reps, rest times, and progression tips.",
    "category": "generate",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "goal": {
            "type": "string",
            "enum": [
                "strength",
                "hypertrophy",
                "endurance",
                "fat_loss",
                "general_fitness"
            ],
            "description": "Primary fitness objective that determines rep ranges, volume, and intensity guidelines."
        },
        "equipment": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "barbell",
                    "dumbbell",
                    "kettlebell",
                    "resistance_bands",
                    "bodyweight",
                    "cable_machine",
                    "smith_machine",
                    "cardio_machine"
                ]
            },
            "description": "List of available equipment types to filter exercises that can be performed."
        },
        "days_per_week": {
            "type": "integer",
            "minimum": 2,
            "maximum": 6,
            "description": "Number of training days per week, used to split muscle groups or sessions appropriately."
        },
        "experience_level": {
            "type": "string",
            "enum": [
                "beginner",
                "intermediate",
                "advanced"
            ],
            "description": "User's training experience level to adjust exercise complexity and load progression."
        },
        "session_duration_minutes": {
            "type": "integer",
            "minimum": 20,
            "maximum": 120,
            "description": "Optional: Target duration per workout session in minutes. Defaults to 60 if not provided."
        }
    },
    "required": [
        "goal",
        "equipment",
        "days_per_week",
        "experience_level"
    ]
},
}
