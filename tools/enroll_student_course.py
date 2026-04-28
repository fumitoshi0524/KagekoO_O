"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Enroll a student in an academic course."""
    import json
    from datetime import date

    try:
        data = json.loads(payload)
        student_id = data.get('student_id')
        course_code = data.get('course_code')
        term = data.get('term')
        enrollment_date = data.get('enrollment_date', date.today().isoformat())

        if not student_id or not course_code or not term:
            return json.dumps({'error': 'Missing required fields: student_id, course_code, term'})

        # Simulate prerequisite and conflict checks
        prerequisites = {'CS201': ['CS101'], 'MATH301': ['MATH201']}
        schedule_conflicts = {'S101': ['10:00-11:30 Mon'], 'S202': ['14:00-15:30 Wed']}
        course_catalog = {
            'CS201': {'name': 'Data Structures', 'credits': 3, 'schedule': '10:00-11:30 Mon'},
            'MATH301': {'name': 'Linear Algebra', 'credits': 3, 'schedule': '09:00-10:30 Tue'}
        }

        if course_code not in course_catalog:
            return json.dumps({'error': f'Course {course_code} not found in catalog'})

        # Check prerequisites
        prereq_list = prerequisites.get(course_code, [])
        for prereq in prereq_list:
            # Simulation: assume student has taken prerequisite if student_id contains 'S'
            if 'S' in student_id:
                continue
            else:
                return json.dumps({'error': f'Missing prerequisite: {prereq}'})

        # Check schedule conflict (simulate based on if student already enrolled in a conflicting slot)
        course_schedule = course_catalog[course_code]['schedule']
        conflict = False
        for existing_schedule in schedule_conflicts.get(student_id, []):
            if existing_schedule == course_schedule:
                conflict = True
                break
        if conflict:
            return json.dumps({'error': 'Schedule conflict detected with existing enrollment'})

        # Enroll student (simulate)
        enrollment_id = f"ENR-{student_id}-{course_code}-{term.replace('-','')}"
        result = {
            'status': 'enrolled',
            'enrollment_id': enrollment_id,
            'student_id': student_id,
            'course_code': course_code,
            'course_name': course_catalog[course_code]['name'],
            'credits': course_catalog[course_code]['credits'],
            'term': term,
            'enrollment_date': enrollment_date,
            'schedule': course_schedule
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "enroll_student_course",
    "description": "Enroll a student in an academic course, validating prerequisites, checking for schedule conflicts, and returning enrollment confirmation with course details and student schedule summary.",
    "category": "operations",
    "domain": "education",
    "risk_level": "high",
    "schema": {
    "type": "object",
    "properties": {
        "student_id": {
            "type": "string",
            "description": "Unique identifier for the student (alphanumeric, up to 20 characters)."
        },
        "course_code": {
            "type": "string",
            "description": "Course code (e.g., 'CS101') representing the course to enroll in."
        },
        "term": {
            "type": "string",
            "description": "Academic term identifier (e.g., '2025-Spring', '2025-Fall')."
        },
        "enrollment_date": {
            "type": "string",
            "description": "Optional: Date of enrollment in YYYY-MM-DD format. Defaults to current date if not provided."
        }
    },
    "required": [
        "student_id",
        "course_code",
        "term"
    ]
},
}
