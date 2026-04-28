"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage student enrollment in academic courses."""
    import json
    try:
        data = json.loads(payload)
        action = data.get('action')
        student_id = data.get('student_id')
        course_code = data.get('course_code')
        academic_term = data.get('academic_term')
        section_id = data.get('section_id', 'DEFAULT')
        reason = data.get('reason', '')

        if not all([action, student_id, course_code, academic_term]):
            return json.dumps({'status': 'error', 'message': 'Missing required fields: action, student_id, course_code, academic_term'})

        # In-memory enrollment store (simulated)
        enrollment_store = {
            'STU-2024-001': [{'course': 'CS-101', 'section': 'SEC-A', 'term': '2024-FALL', 'status': 'enrolled', 'grade': ''}],
            'STU-2024-002': [{'course': 'MATH-201', 'section': 'SEC-B', 'term': '2024-FALL', 'status': 'enrolled', 'grade': ''}]
        }
        course_catalog = {
            'CS-101': {'name': 'Introduction to Computer Science', 'capacity': 100, 'enrolled': 85, 'prerequisites': []},
            'MATH-201': {'name': 'Calculus II', 'capacity': 80, 'enrolled': 78, 'prerequisites': ['MATH-101']},
            'PHYS-301': {'name': 'Quantum Mechanics', 'capacity': 60, 'enrolled': 60, 'prerequisites': ['PHYS-201', 'MATH-201']}
        }
        waitlist = {}

        if action == 'enroll':
            if course_code not in course_catalog:
                return json.dumps({'status': 'error', 'message': f'Course {course_code} not found in catalog'})
            course = course_catalog[course_code]
            if course['enrolled'] >= course['capacity']:
                return json.dumps({'status': 'error', 'message': f'Course {course_code} is at full capacity ({course["capacity"]})'})
            if student_id not in enrollment_store:
                enrollment_store[student_id] = []
            for enrollment in enrollment_store[student_id]:
                if enrollment['course'] == course_code and enrollment['term'] == academic_term and enrollment['status'] == 'enrolled':
                    return json.dumps({'status': 'error', 'message': f'Student {student_id} is already enrolled in {course_code} for {academic_term}'})
            enrollment_store[student_id].append({
                'course': course_code,
                'section': section_id,
                'term': academic_term,
                'status': 'enrolled',
                'grade': ''
            })
            course_catalog[course_code]['enrolled'] += 1
            return json.dumps({
                'status': 'success',
                'message': f'Student {student_id} enrolled in {course_code} section {section_id} for {academic_term}',
                'enrollment_record': {
                    'student_id': student_id,
                    'course_code': course_code,
                    'section_id': section_id,
                    'academic_term': academic_term,
                    'status': 'enrolled',
                    'total_enrolled': course_catalog[course_code]['enrolled'],
                    'capacity': course_catalog[course_code]['capacity']
                }
            })

        elif action == 'withdraw':
            if student_id not in enrollment_store:
                return json.dumps({'status': 'error', 'message': f'Student {student_id} has no enrollments'})
            found = False
            for enrollment in enrollment_store[student_id]:
                if enrollment['course'] == course_code and enrollment['term'] == academic_term:
                    enrollment['status'] = 'withdrawn'
                    enrollment['reason'] = reason
                    if course_code in course_catalog:
                        course_catalog[course_code]['enrolled'] = max(0, course_catalog[course_code]['enrolled'] - 1)
                    found = True
                    break
            if not found:
                return json.dumps({'status': 'error', 'message': f'No enrollment found for student {student_id} in course {course_code} for {academic_term}'})
            return json.dumps({
                'status': 'success',
                'message': f'Student {student_id} withdrawn from {course_code} for {academic_term}',
                'withdrawal_record': {
                    'student_id': student_id,
                    'course_code': course_code,
                    'academic_term': academic_term,
                    'status': 'withdrawn',
                    'reason': reason
                }
            })

        elif action == 'waitlist':
            course = course_catalog.get(course_code)
            if not course:
                return json.dumps({'status': 'error', 'message': f'Course {course_code} not found'})
            key = f'{course_code}_{academic_term}_{section_id}'
            if key not in waitlist:
                waitlist[key] = []
            if student_id in waitlist[key]:
                return json.dumps({'status': 'error', 'message': f'Student {student_id} is already on waitlist for {course_code} section {section_id}'})
            waitlist[key].append(student_id)
            return json.dumps({
                'status': 'success',
                'message': f'Student {student_id} added to waitlist for {course_code} section {section_id} (position {len(waitlist[key])})',
                'waitlist_record': {
                    'student_id': student_id,
                    'course_code': course_code,
                    'section_id': section_id,
                    'academic_term': academic_term,
                    'waitlist_position': len(waitlist[key]),
                    'available_seats': course['capacity'] - course['enrolled']
                }
            })

        elif action == 'transfer_section':
            new_section_id = data.get('new_section_id')
            if not new_section_id:
                return json.dumps({'status': 'error', 'message': 'new_section_id is required for transfer_section action'})
            if student_id not in enrollment_store:
                return json.dumps({'status': 'error', 'message': f'Student {student_id} has no enrollments'})
            found = False
            for enrollment in enrollment_store[student_id]:
                if enrollment['course'] == course_code and enrollment['term'] == academic_term and enrollment['status'] == 'enrolled':
                    old_section = enrollment['section']
                    enrollment['section'] = new_section_id
                    found = True
                    break
            if not found:
                return json.dumps({'status': 'error', 'message': f'No active enrollment found for transfer'})
            return json.dumps({
                'status': 'success',
                'message': f'Student {student_id} transferred from section {old_section} to {new_section_id} for {course_code}',
                'transfer_record': {
                    'student_id': student_id,
                    'course_code': course_code,
                    'academic_term': academic_term,
                    'old_section': old_section,
                    'new_section': new_section_id,
                    'reason': reason
                }
            })

        else:
            return json.dumps({'status': 'error', 'message': f'Invalid action: {action}. Must be one of: enroll, withdraw, waitlist, transfer_section'})

    except json.JSONDecodeError as e:
        return json.dumps({'status': 'error', 'message': f'Invalid JSON payload: {str(e)}'})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': f'Enrollment processing failed: {str(e)}'})


TOOL_SPEC = {
    "name": "student_enrollment_manager",
    "description": "Manage student enrollment in academic courses, supporting enrollment, withdrawal, and waitlist operations while tracking enrollment status, prerequisites completion, and course capacity limits.",
    "category": "operations",
    "domain": "education",
    "risk_level": "medium",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The enrollment operation to perform",
            "enum": [
                "enroll",
                "withdraw",
                "waitlist",
                "transfer_section"
            ]
        },
        "student_id": {
            "type": "string",
            "description": "Unique identifier for the student",
            "examples": [
                "STU-2024-001",
                "S12345"
            ]
        },
        "course_code": {
            "type": "string",
            "description": "Course identifier code in format DEPT-NUMBER",
            "examples": [
                "CS-101",
                "MATH-201",
                "PHYS-301"
            ]
        },
        "section_id": {
            "type": "string",
            "description": "Optional: Specific section identifier for the course offering",
            "examples": [
                "SEC-A",
                "SEC-B",
                "ONLINE-01"
            ]
        },
        "academic_term": {
            "type": "string",
            "description": "Academic term identifier for the enrollment period",
            "examples": [
                "2024-FALL",
                "2025-SPRING",
                "2024-SUMMER"
            ]
        },
        "reason": {
            "type": "string",
            "description": "Optional: Reason for withdrawal or transfer action",
            "examples": [
                "schedule_conflict",
                "prerequisite_not_met",
                "personal_reasons"
            ]
        }
    },
    "required": [
        "action",
        "student_id",
        "course_code",
        "academic_term"
    ]
},
}
