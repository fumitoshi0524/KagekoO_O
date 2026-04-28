"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        student_id = data.get('student_id')
        course_code = data.get('course_code')
        section_number = data.get('section_number')
        term = data.get('term')
        prerequisite_override = data.get('prerequisite_override', False)
        
        if not student_id or not course_code or not section_number or not term:
            return json.dumps({'error': 'Missing required fields: student_id, course_code, section_number, term'})
        
        # Simulate course catalog and section data
        courses = {
            'CS101': {'name': 'Intro to CS', 'prerequisites': [], 'capacity': 30},
            'MATH201': {'name': 'Calculus II', 'prerequisites': ['MATH101'], 'capacity': 25}
        }
        
        if course_code not in courses:
            return json.dumps({'error': 'Course not found'})
        
        course = courses[course_code]
        
        # Check if prerequisites are met (simple simulation)
        if not prerequisite_override and course['prerequisites']:
            # Simulate checking prerequisites (e.g., student has completed MATH101)
            # In a real system, would query student's transcript
            return json.dumps({'error': f'Missing prerequisites: {course["prerequisites"]}'})
        
        # Simulate capacity check
        # Assume each section has a fixed capacity; here we just check if section_number exists
        # For simplicity, we assume capacity is available unless explicitly full
        if section_number not in ['A', 'B', '01', '02']:
            return json.dumps({'error': 'Invalid section number'})
        
        # Simulate successful enrollment
        enrollment = {
            'status': 'enrolled',
            'student_id': student_id,
            'course_code': course_code,
            'course_name': course['name'],
            'section': section_number,
            'term': term,
            'enrollment_id': f'{student_id}-{course_code}-{section_number}-{term}'
        }
        return json.dumps(enrollment, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "enroll_student",
    "description": "Enroll a student in a specific course section for a given academic term, handling capacity checks and prerequisite validation, and returning an enrollment confirmation with section details.",
    "category": "operations",
    "domain": "education",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "student_id": {
            "type": "string",
            "description": "Unique identifier for the student (e.g., student email or ID number)."
        },
        "course_code": {
            "type": "string",
            "description": "Course code of the course to enroll in (e.g., 'CS101')."
        },
        "section_number": {
            "type": "string",
            "description": "Section number for the course offering (e.g., 'A' or '01')."
        },
        "term": {
            "type": "string",
            "description": "Academic term identifier, e.g., '2024-Fall'."
        },
        "prerequisite_override": {
            "type": "boolean",
            "description": "Optional: Set to true to bypass prerequisite checks for administrative override.",
            "default": false
        }
    },
    "required": [
        "student_id",
        "course_code",
        "section_number",
        "term"
    ]
},
}
