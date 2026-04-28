"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        topic = data.get('topic')
        grade_level = data.get('grade_level')
        duration = data.get('duration_minutes')
        if not topic or not grade_level or not duration:
            return json.dumps({'error': 'Missing required fields: topic, grade_level, duration_minutes'})
        if duration < 15 or duration > 180:
            return json.dumps({'error': 'Duration must be between 15 and 180 minutes'})
        valid_grades = ['preschool', 'kindergarten', 'elementary', 'middle_school', 'high_school', 'college', 'adult_education']
        if grade_level not in valid_grades:
            return json.dumps({'error': f'Invalid grade_level. Must be one of: {valid_grades}'})
        teaching_style = data.get('teaching_style', 'interactive')
        include_assessment = data.get('include_assessment', True)
        # Generate lesson plan components based on inputs
        objectives = [
            f'Understand key concepts of {topic}',
            f'Apply knowledge of {topic} to real-world examples',
            f'Analyze and discuss the significance of {topic}'
        ]
        materials = ['Whiteboard or projector', 'Handouts or digital worksheet', 'Access to internet (for research)']
        if grade_level in ['elementary', 'middle_school']:
            materials.append('Art supplies for creative activity')
        elif grade_level in ['high_school', 'college']:
            materials.append('Textbook or scholarly article')
        # Activity phases based on duration
        intro_min = max(5, int(duration * 0.15))
        main_min = max(10, int(duration * 0.55))
        practice_min = duration - intro_min - main_min
        if practice_min < 5:
            practice_min = 5
            intro_min = max(5, int((duration - practice_min) * 0.4))
            main_min = duration - intro_min - practice_min
        activities = [
            {'phase': 'Introduction', 'duration_min': intro_min, 'description': f'Introduce {topic} with a hook question or short video to activate prior knowledge'},
            {'phase': 'Main Instruction', 'duration_min': main_min, 'description': f'Teach core concepts of {topic} using {teaching_style} methodology. Include examples, diagrams, and guided discussion.'},
            {'phase': 'Practice/Application', 'duration_min': practice_min, 'description': f'Students apply learning through group work, problem-solving, or hands-on activity related to {topic}.'}
        ]
        if include_assessment:
            assessment = {
                'type': 'formative',
                'questions': [
                    f'What is one key fact about {topic}?',
                    f'How does {topic} relate to everyday life?',
                    f'What is one question you still have about {topic}?'
                ],
                'rubric': 'Participation and accuracy of responses'
            }
        else:
            assessment = {'type': 'none', 'description': 'No formal assessment included'}
        lesson_plan = {
            'topic': topic,
            'grade_level': grade_level,
            'duration_minutes': duration,
            'teaching_style': teaching_style,
            'learning_objectives': objectives,
            'materials': materials,
            'activities': activities,
            'assessment': assessment,
            'summary': f'A {duration}-minute lesson on {topic} for {grade_level} using {teaching_style} approach.'
        }
        return json.dumps(lesson_plan, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})



TOOL_SPEC = {
    "name": "generate_lesson_plan",
    "description": "Generate a comprehensive lesson plan for a given topic, grade level, and duration, including learning objectives, materials, activities, and assessment methods. Returns a structured lesson plan object suitable for classroom or curriculum use.",
    "category": "generate",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "The subject or topic for the lesson plan (e.g., 'Photosynthesis', 'World War II', 'Introduction to Fractions')"
        },
        "grade_level": {
            "type": "string",
            "enum": [
                "preschool",
                "kindergarten",
                "elementary",
                "middle_school",
                "high_school",
                "college",
                "adult_education"
            ],
            "description": "The target educational level for the lesson"
        },
        "duration_minutes": {
            "type": "integer",
            "minimum": 15,
            "maximum": 180,
            "description": "Total duration of the lesson in minutes (15-180)"
        },
        "teaching_style": {
            "type": "string",
            "enum": [
                "lecture",
                "interactive",
                "project_based",
                "inquiry_based",
                "gamified",
                "flipped_classroom"
            ],
            "description": "Optional: Preferred teaching methodology. Default is 'interactive'.",
            "default": "interactive"
        },
        "include_assessment": {
            "type": "boolean",
            "description": "Optional: Whether to include assessment questions or rubric. Default is True."
        }
    },
    "required": [
        "topic",
        "grade_level",
        "duration_minutes"
    ]
},
}
