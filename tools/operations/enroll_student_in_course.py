"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import uuid
    from datetime import datetime

    try:
        data = json.loads(payload)
        # Validate required fields
        required = ['student_id', 'course_code', 'section_id', 'term']
        for field in required:
            if field not in data or not data[field]:
                return json.dumps({'error': f'Missing required field: {field}'})

        student_id = data['student_id']
        course_code = data['course_code']
        section_id = data['section_id']
        term = data['term']
        enrollment_mode = data.get('enrollment_mode', 'credit')
        override_prereqs = data.get('override_prerequisites', False)

        # Simulate course catalog lookup (in real system, fetch from DB)
        course_catalog = {
            'MATH101': {'title': 'Calculus I', 'prerequisites': [], 'capacity': 100, 'sections': {'A': 90, 'B': 85}},
            'ENG202': {'title': 'Advanced Composition', 'prerequisites': ['ENG101'], 'capacity': 60, 'sections': {'01': 55, '02': 60}},
            'PHY201': {'title': 'Physics for Engineers', 'prerequisites': ['MATH101', 'PHY101'], 'capacity': 80, 'sections': {'L1': 45, 'L2': 50}},
        }

        if course_code not in course_catalog:
            return json.dumps({'error': f'Course {course_code} not found in catalog'})

        course = course_catalog[course_code]
        if section_id not in course['sections']:
            return json.dumps({'error': f'Section {section_id} not found for course {course_code}'})

        # Check prerequisites
        if not override_prereqs and course['prerequisites']:
            # Simulate student's completed courses (in real system, fetch from student records)
            student_completed = {'MATH101': True, 'ENG101': True, 'MATH201': False}
            for prereq in course['prerequisites']:
                if not student_completed.get(prereq, False):
                    return json.dumps({'error': f'Prerequisite {prereq} not completed for {course_code}'})

        # Check capacity
        current_enrollment = course['sections'][section_id]
        if current_enrollment >= course['capacity']:
            waitlist_position = 1  # simplified; real system would assign position
            result = {
                'status': 'waitlisted',
                'student_id': student_id,
                'course_code': course_code,
                'section_id': section_id,
                'term': term,
                'enrollment_mode': enrollment_mode,
                'enrolled': False,
                'waitlist_position': waitlist_position,
                'message': f'Section full. Added to waitlist at position {waitlist_position}.'
            }
            return json.dumps(result)

        # Generate enrollment ID and timestamp
        enrollment_id = str(uuid.uuid4())
        enrolled_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        result = {
            'status': 'enrolled',
            'enrollment_id': enrollment_id,
            'student_id': student_id,
            'course_code': course_code,
            'course_title': course['title'],
            'section_id': section_id,
            'term': term,
            'enrollment_mode': enrollment_mode,
            'enrolled_at': enrolled_at,
            'message': f'Successfully enrolled in {course_code} {section_id} for {term}.'
        }
        return json.dumps(result)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "enroll_student_in_course",
    "description": "Enroll a student into a specific academic course section, validating prerequisites, capacity, and schedule conflicts. Returns enrollment confirmation with a unique enrollment ID, session details, and any applied waitlist status.",
    "category": "operations",
    "domain": "education",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "student_id": {
            "type": "string",
            "description": "Unique identifier for the student (e.g., student ID from the SIS system)."
        },
        "course_code": {
            "type": "string",
            "description": "Official course code (e.g., 'MATH101', 'ENG202'). Must match a valid course in the catalog."
        },
        "section_id": {
            "type": "string",
            "description": "Specific section identifier (e.g., 'A', '01', 'MWF-10AM'). Must exist for the given course."
        },
        "term": {
            "type": "string",
            "description": "Academic term code (e.g., 'FA2024', 'SP2025'). Current active term used for enrollment validation."
        },
        "enrollment_mode": {
            "type": "string",
            "description": "Optional: Enrollment mode. Options: 'credit', 'audit', 'pass_fail'.",
            "enum": [
                "credit",
                "audit",
                "pass_fail"
            ],
            "default": "credit"
        },
        "override_prerequisites": {
            "type": "boolean",
            "description": "Optional: Force enrollment even if prerequisites are not met (requires admin approval). Default False.",
            "default": False
        }
    },
    "required": [
        "student_id",
        "course_code",
        "section_id",
        "term"
    ]
},
}
