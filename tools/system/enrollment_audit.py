"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        enrollments = data.get('enrollments', [])
        courses = data.get('courses', [])
        student_records = data.get('student_records', {})
        
        # Build course lookup
        course_map = {}
        for c in courses:
            course_map[c['course_code']] = c
        
        # Count enrollments per course
        enrollment_counts = {}
        for e in enrollments:
            code = e['course_code']
            if code not in enrollment_counts:
                enrollment_counts[code] = 0
            enrollment_counts[code] += 1
        
        # Build audit reports
        capacity_issues = []
        prerequisite_issues = []
        
        for e in enrollments:
            student_id = e['student_id']
            course_code = e['course_code']
            course = course_map.get(course_code)
            
            if course:
                # Capacity check (check once per course)
                count = enrollment_counts[course_code]
                if count > course['capacity']:
                    issue = f"Course {course_code} has {count} enrollments, exceeds capacity {course['capacity']}"
                    if issue not in capacity_issues:
                        capacity_issues.append(issue)
                
                # Prerequisite check
                for prereq in course.get('prerequisites', []):
                    completed = student_records.get(student_id, [])
                    if prereq not in completed:
                        prerequisite_issues.append({
                            'student_id': student_id,
                            'course_code': course_code,
                            'missing_prerequisite': prereq
                        })
        
        result = {
            'total_enrollments': len(enrollments),
            'total_courses': len(courses),
            'capacity_violations': len(capacity_issues),
            'prerequisite_violations': len(prerequisite_issues),
            'capacity_issues': capacity_issues,
            'prerequisite_issues': prerequisite_issues,
            'compliance_status': 'pass' if len(capacity_issues) == 0 and len(prerequisite_issues) == 0 else 'fail'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "enrollment_audit",
    "description": "Analyze student enrollment records against course capacity limits and prerequisite requirements, returning a detailed audit report with compliance status, over-capacity warnings, and prerequisite violations.",
    "category": "system",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "enrollments": {
            "type": "array",
            "description": "List of student enrollment records with course codes and enrollment dates.",
            "items": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "Unique identifier for the student."
                    },
                    "course_code": {
                        "type": "string",
                        "description": "Course code, e.g. MATH101."
                    },
                    "enrollment_date": {
                        "type": "string",
                        "description": "Enrollment date in YYYY-MM-DD format."
                    }
                }
            }
        },
        "courses": {
            "type": "array",
            "description": "List of course definitions with capacity limits and prerequisite course codes.",
            "items": {
                "type": "object",
                "properties": {
                    "course_code": {
                        "type": "string",
                        "description": "Course code, e.g. MATH101."
                    },
                    "capacity": {
                        "type": "integer",
                        "description": "Maximum number of students allowed."
                    },
                    "prerequisites": {
                        "type": "array",
                        "description": "List of prerequisite course codes, empty if none.",
                        "items": {
                            "type": "string"
                        }
                    }
                }
            }
        },
        "student_records": {
            "type": "object",
            "description": "Optional: Mapping of student_id to list of previously completed course codes for prerequisite validation.",
            "additionalProperties": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        }
    },
    "required": [
        "enrollments",
        "courses"
    ]
},
}
