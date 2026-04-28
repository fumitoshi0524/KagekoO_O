"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a personalized weekly sports training plan."""
    import json
    import random

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ["sport", "fitness_level", "goal", "days_per_week"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)

        sport = data["sport"]
        fitness_level = data["fitness_level"]
        goal = data["goal"]
        days_per_week = data["days_per_week"]
        session_duration = data.get("session_duration_minutes", 45)
        preferred_rest = data.get("preferred_rest_day", "")

        # Base workout templates per sport
        workout_templates = {
            "running": {
                "endurance": ["Long slow run", "Tempo run", "Easy recovery run", "Fartlek", "Hill repeats"],
                "strength": ["Hill sprints", "Strides", "Plyometric drills", "Strength circuit", "Trail run"],
                "speed": ["Interval training", "Track repeats", "Strides", "Progression run", "Sprint drills"],
                "flexibility": ["Yoga for runners", "Dynamic stretching", "Form drills", "Easy jog + stretching", "Recovery walk"],
                "general_maintenance": ["Easy run", "Cross-training", "Recovery jog", "Mix run", "Active recovery"]
            },
            "swimming": {
                "endurance": ["Distance freestyle", "Pull buoy set", "Kick set", "IM set", "Continuous swim"],
                "strength": ["Power paddles set", "Sprint set", "Strength pull set", "Drill set", "Resistance work"],
                "speed": ["Sprint intervals", "Descending sets", "Broken swims", "Fast pace work", "Sprint kick"],
                "flexibility": ["Stretch and swim", "Technique drills", "Easy recovery", "Yoga flow", "Flexibility set"],
                "general_maintenance": ["Mixed set", "Technique focus", "Drill work", "Endurance set", "Recovery swim"]
            },
            "cycling": {
                "endurance": ["Long endurance ride", "Zone 2 ride", "Tempo ride", "Recovery spin", "Hill climb ride"],
                "strength": ["Hill repeats", "Big gear pushes", "Sprint efforts", "Strength intervals", "Resistance ride"],
                "speed": ["Interval repeats", "Sprint intervals", "Fast group ride", "Time trial effort", "Speed play"],
                "flexibility": ["Easy recovery spin", "Stretching ride", "Yoga for cyclists", "Technique drills", "Active recovery"],
                "general_maintenance": ["Group ride", "Mixed terrain ride", "Cross-training", "Easy spin", "Recovery ride"]
            },
            "basketball": {
                "endurance": ["Full court scrimmage", "Conditioning drills", "Transition drills", "Defensive slides", "Sprinting drills"],
                "strength": ["Weight training", "Plyometrics", "Strength drills", "Resistance training", "Core work"],
                "speed": ["Agility ladder", "Sprint drills", "Quickness drills", "First step work", "Speed dribbling"],
                "flexibility": ["Yoga for basketball", "Dynamic warmup", "Static stretching", "Foam rolling", "Mobility work"],
                "general_maintenance": ["Shooting practice", "Dribbling drills", "Pickup game", "Skill work", "Team practice"]
            },
            "soccer": {
                "endurance": ["Small-sided games", "Interval runs", "Circuit training", "Continuous play", "Track work"],
                "strength": ["Strength circuit", "Plyometric drills", "Core work", "Resistance bands", "Leg strength"],
                "speed": ["Sprint intervals", "Agility drills", "Speed ladder", "Quick feet drills", "Change of direction"],
                "flexibility": ["Dynamic stretching", "Yoga for soccer", "Recovery session", "Mobility routine", "Cool down"],
                "general_maintenance": ["Skills practice", "Team training", "Scrimmage", "Conditioning", "Technical work"]
            },
            "general_fitness": {
                "endurance": ["Circuit training", "Cardio mix", "HIIT session", "Steady state cardio", "Interval training"],
                "strength": ["Full body strength", "Upper body focus", "Lower body focus", "Core and strength", "Compound lifts"],
                "speed": ["Plyometric workout", "Agility drills", "Speed intervals", "Quickness circuit", "Explosive work"],
                "flexibility": ["Yoga session", "Stretching routine", "Mobility drill", "Pilates", "Recovery flow"],
                "general_maintenance": ["Mixed workout", "Activity of choice", "Light movement", "Recreation", "Active recovery"]
            }
        }

        intensity_map = {
            "beginner": "low",
            "intermediate": "moderate",
            "advanced": "high"
        }

        intensity_labels = {
            "low": "Light effort, focus on form",
            "moderate": "Challenging but sustainable",
            "high": "High intensity, near-maximum effort"
        }

        # Generate weekly schedule
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Handle preferred rest days
        rest_days = []
        if preferred_rest:
            rest_days = [d.strip().capitalize() for d in preferred_rest.split(",")]
            rest_days = [d for d in rest_days if d in days_of_week]

        # Determine total rest days needed
        total_rest = 7 - days_per_week
        if len(rest_days) < total_rest:
            available = [d for d in days_of_week if d not in rest_days]
            random.shuffle(available)
            rest_days.extend(available[:total_rest - len(rest_days)])
        elif len(rest_days) > total_rest:
            rest_days = rest_days[:total_rest]

        training_days = [d for d in days_of_week if d not in rest_days]

        # Get appropriate workouts
        sport_templates = workout_templates.get(sport, workout_templates["general_fitness"])
        goal_workouts = sport_templates.get(goal, sport_templates["general_maintenance"])

        # Shuffle and assign workouts
        random.shuffle(goal_workouts)
        schedule = []
        intensity = intensity_map.get(fitness_level, "moderate")

        for i, day in enumerate(training_days):
            workout = goal_workouts[i % len(goal_workouts)]
            schedule.append({
                "day": day,
                "workout": workout,
                "duration_minutes": session_duration,
                "intensity": intensity,
                "intensity_note": intensity_labels[intensity],
                "progression_tip": f"Focus on quality over quantity. Listen to your body."
            })

        rest_schedule = []
        for day in rest_days:
            rest_schedule.append({
                "day": day,
                "workout": "Rest day / Active recovery",
                "duration_minutes": 0,
                "intensity": "rest",
                "intensity_note": "Complete rest or light stretching/walking",
                "progression_tip": "Recovery is essential for progress. Stay hydrated."
            })

        # Combine and sort by day order
        full_schedule = schedule + rest_schedule
        day_order = {d: i for i, d in enumerate(days_of_week)}
        full_schedule.sort(key=lambda x: day_order[x["day"]])

        result = {
            "sport": sport,
            "fitness_level": fitness_level,
            "goal": goal,
            "weekly_schedule": full_schedule,
            "summary": f"{days_per_week}-day {goal} training plan for {sport} at {fitness_level} level. Sessions are {session_duration} minutes with {intensity} intensity."
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_training_plan",
    "description": "Generate a personalized weekly sports training plan based on sport type, current fitness level, and goal (e.g., endurance, strength, speed). Returns a structured schedule with daily workouts, rest days, and progression tips.",
    "category": "generate",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "sport": {
            "type": "string",
            "description": "Primary sport or activity type (e.g., running, swimming, cycling, basketball, soccer, general fitness).",
            "enum": [
                "running",
                "swimming",
                "cycling",
                "basketball",
                "soccer",
                "general_fitness"
            ]
        },
        "fitness_level": {
            "type": "string",
            "description": "Current fitness level of the athlete.",
            "enum": [
                "beginner",
                "intermediate",
                "advanced"
            ]
        },
        "goal": {
            "type": "string",
            "description": "Training focus or goal for the week.",
            "enum": [
                "endurance",
                "strength",
                "speed",
                "flexibility",
                "general_maintenance"
            ]
        },
        "days_per_week": {
            "type": "integer",
            "description": "Number of training days per week (between 1 and 7).",
            "minimum": 1,
            "maximum": 7
        },
        "session_duration_minutes": {
            "type": "integer",
            "description": "Optional: Preferred duration of each training session in minutes (default 45).",
            "minimum": 15,
            "maximum": 180
        },
        "preferred_rest_day": {
            "type": "string",
            "description": "Optional: Preferred rest day(s) during the week (e.g., Sunday, Wednesday). Comma-separated if multiple.",
            "examples": [
                "Wednesday",
                "Sunday"
            ]
        }
    },
    "required": [
        "sport",
        "fitness_level",
        "goal",
        "days_per_week"
    ]
},
}
