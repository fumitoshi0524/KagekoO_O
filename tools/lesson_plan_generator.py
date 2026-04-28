"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a structured lesson plan."""
    import json
    import random

    try:
        data = json.loads(payload)
        topic = data.get("topic")
        grade_level = data.get("grade_level")
        duration_minutes = data.get("duration_minutes")
        teaching_style = data.get("teaching_style", "interactive")
        additional_notes = data.get("additional_notes", "")

        if not topic or not grade_level or not duration_minutes:
            return json.dumps({"error": "Missing required fields: topic, grade_level, duration_minutes"})

        if not isinstance(duration_minutes, int) or duration_minutes < 15 or duration_minutes > 180:
            return json.dumps({"error": "duration_minutes must be an integer between 15 and 180"})

        # Generate lesson structure based on duration
        intro_time = max(5, int(duration_minutes * 0.12))
        main_act_time = int(duration_minutes * 0.45)
        practice_time = int(duration_minutes * 0.25)
        wrap_up_time = duration_minutes - intro_time - main_act_time - practice_time
        if wrap_up_time < 5:
            wrap_up_time = 5
            main_act_time = duration_minutes - intro_time - practice_time - 5

        # Generate objectives (2-4)
        objectives = [
            f"Understand key concepts of {topic}",
            f"Apply knowledge of {topic} to real-world examples",
            f"Analyze and discuss different perspectives on {topic}",
        ]
        if random.choice([True, False]):
            objectives.append(f"Create a summary or presentation on {topic}")

        # Generate activities based on style
        activities = []
        if teaching_style == "interactive":
            activities = [
                {"name": "Think-Pair-Share brainstorm on 'Why is this topic important?', time_minutes": 8},
                {"name": "Small group discussion with guiding questions", "time_minutes": 12},
                {"name": "Mini-lecture with visual aids (5 min)", "time_minutes": 5},
            ]
        elif teaching_style == "project-based":
            activities = [
                {"name": "Introduce driving question for a mini-project", "time_minutes": 10},
                {"name": "Students form teams and plan approach", "time_minutes": 15},
                {"name": "Hands-on creation or research time", "time_minutes": 20},
            ]
        elif teaching_style == "discussion":
            activities = [
                {"name": "Opening reading or video clip related to topic", "time_minutes": 5},
                {"name": "Socratic seminar with prepared questions", "time_minutes": 25},
                {"name": "Debate on a controversial aspect", "time_minutes": 15},
            ]
        else:  # lecture
            activities = [
                {"name": "Structured lecture with slides and examples", "time_minutes": 20},
                {"name": "Demonstration or case study analysis", "time_minutes": 15},
                {"name": "Q&A session", "time_minutes": 10},
            ]

        # Generate practice activity
        practice_types = ["worksheet", "group problem-solving", "online quiz", "reflective journaling"]
        practice_type = random.choice(practice_types)

        # Generate assessment
        assessment_methods = ["Exit ticket with 3 questions", "Short quiz (5 items)", "Oral check-in"]
        assessment = random.choice(assessment_methods)

        # Generate materials list
        materials = [
            "Whiteboard or projector",
            "Handouts with key terms",
            "Student notebooks or digital devices",
        ]
        if practice_type == "worksheet":
            materials.append("Printed worksheet")
        elif practice_type == "online quiz":
            materials.append("Access to quiz platform")

        lesson_plan = {
            "topic": topic,
            "grade_level": grade_level,
            "duration_minutes": duration_minutes,
            "teaching_style": teaching_style,
            "learning_objectives": objectives,
            "structure": {
                "introduction": {
                    "time_minutes": intro_time,
                    "activity": f"Hook activity: Ask students what they already know about {topic}. Present learning objectives."
                },
                "main_activities": {
                    "time_minutes": main_act_time,
                    "activities": activities
                },
                "guided_practice": {
                    "time_minutes": practice_time,
                    "activity": f"Students complete {practice_type} related to {topic}. Teacher circulates and provides support."
                },
                "wrap_up": {
                    "time_minutes": wrap_up_time,
                    "activity": f"Recap key takeaways. Assessment: {assessment}. Preview next topic."
                }
            },
            "assessment": assessment,
            "materials": materials,
            "additional_notes": additional_notes if additional_notes else "None"
        }

        return json.dumps(lesson_plan, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"})
    except Exception as e:
        return f"error: {e}"



TOOL_SPEC = {
    "name": "lesson_plan_generator",
    "description": "Generate a structured lesson plan for a given topic, grade level, and duration, including learning objectives, activities, materials, and assessment suggestions. Returns a complete JSON lesson plan with sections for introduction, main activities, practice, and wrap-up.",
    "category": "generate",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Subject or topic for the lesson plan, e.g., 'Photosynthesis' or 'World War II'"
        },
        "grade_level": {
            "type": "string",
            "description": "Target student grade/age level, e.g., 'Grade 5', 'High School Senior', 'Adult Learners'"
        },
        "duration_minutes": {
            "type": "integer",
            "description": "Total length of the lesson in minutes (between 15 and 180)"
        },
        "teaching_style": {
            "type": "string",
            "description": "Optional: Preferred pedagogical approach: 'lecture', 'interactive', 'project-based', or 'discussion'. Default is 'interactive'.",
            "enum": [
                "lecture",
                "interactive",
                "project-based",
                "discussion"
            ]
        },
        "additional_notes": {
            "type": "string",
            "description": "Optional: Any special requirements, class size, available materials, or focus points"
        }
    },
    "required": [
        "topic",
        "grade_level",
        "duration_minutes"
    ]
},
}
