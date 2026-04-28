"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Update the enrollment roster for a specific course section by adding or removing student records, returning the updated list of enrolled students and any conflict notifications."""
    import json
    try:
        data = json.loads(payload)
        course_id = data.get('course_id')
        section_code = data.get('section_code')
        action = data.get('action')
        student_ids = data.get('student_ids')
        term = data.get('term', 'Fall2024')

        if not course_id or not section_code or not action or not student_ids:
            return json.dumps({'error': 'Missing required parameters: course_id, section_code, action, student_ids'})
        if action not in ['add', 'remove']:
            return json.dumps({'error': 'Invalid action. Must be "add" or "remove".'})
        if not isinstance(student_ids, list) or len(student_ids) == 0:
            return json.dumps({'error': 'student_ids must be a non-empty list.'})

        # Simulate database of course sections and rosters
        roster_db = {
            'MATH101_A01_Fall2024': {
                'course_name': 'Calculus I',
                'students': ['STU10001', 'STU10002', 'STU10003'],
                'capacity': 30
            },
            'ENG201_B02_Fall2024': {
                'course_name': 'English Literature',
                'students': ['STU10005', 'STU10006'],
                'capacity': 25
            }
        }

        key = f'{course_id}_{section_code}_{term}'
        if key not in roster_db:
            return json.dumps({'error': f'Course section {course_id} {section_code} for term {term} not found.'})

        section = roster_db[key]
        current_students = set(section['students'])
        conflicts = []
        updated_count = 0

        if action == 'add':
            # Check capacity
            if len(current_students) + len(student_ids) > section['capacity']:
                return json.dumps({'error': f'Cannot add students: would exceed capacity of {section["capacity"]}.'})
            # Check for duplicate enrollment
            for sid in student_ids:
                if sid in current_students:
                    conflicts.append({'student_id': sid, 'issue': 'already enrolled in this section'})
                else:
                    current_students.add(sid)
                    updated_count += 1
        elif action == 'remove':
            for sid in student_ids:
                if sid not in current_students:
                    conflicts.append({'student_id': sid, 'issue': 'not found in roster'})
                else:
                    current_students.remove(sid)
                    updated_count += 1

        # Update roster (in-memory simulation)
        section['students'] = list(current_students)

        result = {
            'status': 'completed',
            'action': action,
            'course_id': course_id,
            'section_code': section_code,
            'term': term,
            'students_affected': updated_count,
            'total_enrolled': len(current_students),
            'enrolled_students': sorted(list(current_students)),
            'conflicts': conflicts,
            'message': f'Successfully {action}ed {updated_count} student(s). {len(conflicts)} conflict(s) detected.'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "classroom_roster_updater",
    "description": "Update the enrollment roster for a specific course section by adding or removing student records, returning the updated list of enrolled students and any conflict notifications.",
    "category": "operations",
    "domain": "education",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "course_id": {
            "type": "string",
            "description": "Unique identifier for the academic course (e.g., 'MATH101')."
        },
        "section_code": {
            "type": "string",
            "description": "Section code for the specific class offering (e.g., 'A01')."
        },
        "action": {
            "type": "string",
            "enum": [
                "add",
                "remove"
            ],
            "description": "Action to perform on the roster: 'add' to enroll a student, 'remove' to withdraw a student."
        },
        "student_ids": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "Unique student identifier (e.g., 'STU12345')."
            },
            "description": "List of one or more student IDs to add or remove from the section roster.",
            "minItems": 1
        },
        "term": {
            "type": "string",
            "description": "Optional: Academic term for the enrollment (e.g., 'Fall2024'). Defaults to current active term if not provided."
        }
    },
    "required": [
        "course_id",
        "section_code",
        "action",
        "student_ids"
    ]
},
}
