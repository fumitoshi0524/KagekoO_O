"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage student enrollments in academic courses."""
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        if action not in ['enroll', 'drop', 'list']:
            return json.dumps({'error': 'Invalid action. Must be enroll, drop, or list.'})
        
        # In-memory enrollment store for demonstration
        if not hasattr(run, 'enrollments'):
            run.enrollments = []
        
        if action == 'list':
            if not run.enrollments:
                return json.dumps({'enrollments': [], 'message': 'No enrollments found.'})
            return json.dumps({'enrollments': run.enrollments})
        
        student_id = data.get('student_id')
        course_code = data.get('course_code')
        semester = data.get('semester')
        
        if not all([student_id, course_code, semester]):
            return json.dumps({'error': 'student_id, course_code, and semester are required for enroll/drop.'})
        
        if action == 'enroll':
            # Check for duplicate enrollment
            for e in run.enrollments:
                if e['student_id'] == student_id and e['course_code'] == course_code and e['semester'] == semester:
                    return json.dumps({'error': 'Student already enrolled in this course for the given semester.'})
            
            enrollment = {
                'student_id': student_id,
                'course_code': course_code,
                'semester': semester,
                'enrollment_date': datetime.now().isoformat()
            }
            run.enrollments.append(enrollment)
            from datetime import datetime
            return json.dumps({'message': 'Enrollment successful.', 'enrollment': enrollment})
        
        elif action == 'drop':
            for i, e in enumerate(run.enrollments):
                if e['student_id'] == student_id and e['course_code'] == course_code and e['semester'] == semester:
                    dropped = run.enrollments.pop(i)
                    return json.dumps({'message': 'Enrollment dropped.', 'dropped': dropped})
            return json.dumps({'error': 'Enrollment not found.'})
            
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "enrollment_manager",
    "description": "Manage student enrollments in academic courses by enrolling new students, dropping existing ones, and listing current enrollments with student and course details.",
    "category": "system",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The enrollment action to perform: enroll a student, drop a student, or list enrollments.",
            "enum": [
                "enroll",
                "drop",
                "list"
            ]
        },
        "student_id": {
            "type": "string",
            "description": "Unique identifier for the student (e.g., email or student number)."
        },
        "course_code": {
            "type": "string",
            "description": "Course identifier (e.g., 'CS101')."
        },
        "semester": {
            "type": "string",
            "description": "Semester or term code (e.g., '2025-Spring')."
        }
    },
    "required": [
        "action"
    ]
},
}
