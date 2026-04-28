"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        course_title = data.get('course_title')
        instructor_name = data.get('instructor_name')
        term = data.get('term')
        topics = data.get('topics', [])
        course_objectives = data.get('course_objectives', ['To be defined by instructor'])
        grading_policy = data.get('grading_policy', 'Assignments 40%, Midterm 30%, Final 30%')
        
        if not course_title or not instructor_name or not term:
            return json.dumps({'error': 'Missing required fields: course_title, instructor_name, term'})
        if not topics or len(topics) == 0:
            return json.dumps({'error': 'At least one topic is required'})
        for t in topics:
            if not t.get('title') or t.get('duration_hours') is None or t.get('duration_hours') <= 0:
                return json.dumps({'error': f'Topic "{t.get("title")}" must have a valid title and positive duration_hours'})
        
        total_hours = sum(t['duration_hours'] for t in topics)
        weeks = []
        for i, topic in enumerate(topics, 1):
            weeks.append({
                'week': i,
                'topic': topic['title'],
                'hours': topic['duration_hours']
            })
        
        syllabus = {
            'course_title': course_title,
            'instructor': instructor_name,
            'term': term,
            'total_duration_hours': total_hours,
            'schedule': weeks,
            'objectives': course_objectives,
            'grading_policy': grading_policy
        }
        return json.dumps(syllabus, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return 'error: Invalid JSON payload'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "create_course_syllabus",
    "description": "Generate a structured course syllabus by accepting course title, instructor name, term, and list of topics with estimated durations, and returns a formatted syllabus document including course objectives, schedule, and grading policy.",
    "category": "operations",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "course_title": {
            "type": "string",
            "description": "The full title of the course (e.g., 'Introduction to Computer Science')."
        },
        "instructor_name": {
            "type": "string",
            "description": "Full name of the course instructor."
        },
        "term": {
            "type": "string",
            "description": "Academic term for the course (e.g., 'Fall 2025', 'Spring 2025')."
        },
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the topic or lecture (e.g., 'Variables and Data Types')."
                    },
                    "duration_hours": {
                        "type": "number",
                        "description": "Estimated duration of this topic in hours."
                    }
                },
                "required": [
                    "title",
                    "duration_hours"
                ]
            },
            "description": "List of topics (each with title and duration in hours) to include in the syllabus. Minimum 1 topic."
        },
        "course_objectives": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of learning objectives for the course (e.g., ['Understand basic programming concepts', 'Build simple algorithms']). Defaults to ['To be defined by instructor']. If provided, must contain at least 1 item."
        },
        "grading_policy": {
            "type": "string",
            "description": "Optional: Description of how students will be evaluated (e.g., 'Assignments 40%, Midterm 30%, Final 30%'). If not provided, a default policy is generated."
        }
    },
    "required": [
        "course_title",
        "instructor_name",
        "term",
        "topics"
    ]
},
}
