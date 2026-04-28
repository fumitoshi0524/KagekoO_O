"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        course_name = data.get('course_name')
        student_scores = data.get('student_scores')
        if not course_name or not student_scores:
            return 'error: Missing required inputs (course_name, student_scores)'
        if not isinstance(student_scores, list) or len(student_scores) == 0:
            return 'error: student_scores must be a non-empty list'
        for score in student_scores:
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                return 'error: All scores must be numbers between 0 and 100'
        # Calculate grade bands
        grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for score in student_scores:
            if score >= 90:
                grade_counts['A'] += 1
            elif score >= 80:
                grade_counts['B'] += 1
            elif score >= 70:
                grade_counts['C'] += 1
            elif score >= 60:
                grade_counts['D'] += 1
            else:
                grade_counts['F'] += 1
        # Compute average
        total = sum(student_scores)
        average = round(total / len(student_scores), 2)
        # Build chart data (simplified representation)
        chart_title = data.get('chart_title', f'Grade Distribution for {course_name}')
        result = {
            'chart_type': 'bar',
            'title': chart_title,
            'course': course_name,
            'grade_counts': grade_counts,
            'total_students': len(student_scores),
            'average_score': average,
            'grade_key': {
                'A': '90-100',
                'B': '80-89',
                'C': '70-79',
                'D': '60-69',
                'F': '0-59'
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "grade_distribution_chart",
    "description": "Generate a grade distribution bar chart for a course or class based on student scores, showing the number of students in each grade band (A, B, C, D, F) and the class average.",
    "category": "visualization",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "course_name": {
            "type": "string",
            "description": "Name of the course or class for the grade distribution."
        },
        "student_scores": {
            "type": "array",
            "items": {
                "type": "number",
                "minimum": 0,
                "maximum": 100
            },
            "description": "List of numerical scores (0-100) for each student in the course."
        },
        "chart_title": {
            "type": "string",
            "description": "Optional: Custom title for the chart. If not provided, defaults to 'Grade Distribution for [course_name]'."
        }
    },
    "required": [
        "course_name",
        "student_scores"
    ]
},
}
