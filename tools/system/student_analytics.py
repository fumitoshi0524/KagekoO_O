"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math

    try:
        data = json.loads(payload)
        students = data.get('students')
        if not students:
            return 'error: students array is required and cannot be empty'
        
        passing_threshold = data.get('passing_threshold', 60)
        risk_threshold = data.get('risk_threshold', 50)
        course_name = data.get('course_name', 'Unknown Course')
        section_name = data.get('section_name', 'Unknown Section')

        if not isinstance(passing_threshold, (int, float)) or passing_threshold < 0 or passing_threshold > 100:
            return 'error: passing_threshold must be a number between 0 and 100'
        if not isinstance(risk_threshold, (int, float)) or risk_threshold < 0 or risk_threshold > 100:
            return 'error: risk_threshold must be a number between 0 and 100'
        if risk_threshold > passing_threshold:
            return 'error: risk_threshold cannot be greater than passing_threshold'

        processed_students = []
        all_grades = []
        passing_count = 0
        at_risk_count = 0

        for student in students:
            s_id = student.get('student_id')
            grades = student.get('grades', [])
            if not isinstance(grades, list) or len(grades) == 0:
                avg = 0.0
                min_grade = 0.0
                max_grade = 0.0
                std_dev = 0.0
                passing = False
                at_risk = True
            else:
                if not all(isinstance(g, (int, float)) and 0 <= g <= 100 for g in grades):
                    return f'error: grades for student {s_id} must be numbers between 0 and 100'
                avg = sum(grades) / len(grades)
                min_grade = min(grades)
                max_grade = max(grades)
                variance = sum((g - avg) ** 2 for g in grades) / len(grades)
                std_dev = math.sqrt(variance)
                passing = avg >= passing_threshold
                at_risk = avg < risk_threshold
                all_grades.extend(grades)
                if passing:
                    passing_count += 1
                if at_risk:
                    at_risk_count += 1

            processed_students.append({
                'student_id': s_id,
                'average': round(avg, 2),
                'min': round(min_grade, 2),
                'max': round(max_grade, 2),
                'std_dev': round(std_dev, 2),
                'passing': passing,
                'at_risk': at_risk
            })

        total_students = len(processed_students)
        overall_avg = round(sum(s['average'] for s in processed_students) / total_students, 2) if total_students > 0 else 0

        result = {
            'course': course_name,
            'section': section_name,
            'total_students': total_students,
            'passing_count': passing_count,
            'passing_rate': round(passing_count / total_students * 100, 2) if total_students > 0 else 0,
            'at_risk_count': at_risk_count,
            'at_risk_rate': round(at_risk_count / total_students * 100, 2) if total_students > 0 else 0,
            'overall_average': overall_avg,
            'overall_min': round(min(all_grades), 2) if all_grades else 0,
            'overall_max': round(max(all_grades), 2) if all_grades else 0,
            'grade_distribution': {
                '90-100': sum(1 for g in all_grades if 90 <= g <= 100),
                '80-89': sum(1 for g in all_grades if 80 <= g < 90),
                '70-79': sum(1 for g in all_grades if 70 <= g < 80),
                '60-69': sum(1 for g in all_grades if 60 <= g < 70),
                'below_60': sum(1 for g in all_grades if g < 60)
            },
            'students': processed_students
        }

        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f'error: Invalid JSON - {e}'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "student_analytics",
    "description": "Aggregate and analyze student performance data across courses, sections, and terms to generate summary statistics, grade distributions, and identify at-risk students based on predefined thresholds.",
    "category": "system",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "students": {
            "type": "array",
            "description": "Array of student records, each containing student_id (string) and grades (array of numbers 0-100).",
            "items": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "Unique identifier for the student."
                    },
                    "grades": {
                        "type": "array",
                        "description": "Array of numeric grades between 0 and 100.",
                        "items": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100
                        }
                    }
                },
                "required": [
                    "student_id",
                    "grades"
                ]
            }
        },
        "passing_threshold": {
            "type": "number",
            "description": "Optional: Minimum average grade considered passing (range 0-100, default 60).",
            "default": 60,
            "minimum": 0,
            "maximum": 100
        },
        "risk_threshold": {
            "type": "number",
            "description": "Optional: Average grade below which a student is considered at-risk (range 0-100, default 50).",
            "default": 50,
            "minimum": 0,
            "maximum": 100
        },
        "course_name": {
            "type": "string",
            "description": "Optional: Name of the course for reporting purposes."
        },
        "section_name": {
            "type": "string",
            "description": "Optional: Name of the course section for granular analysis."
        }
    },
    "required": [
        "students"
    ]
},
}
