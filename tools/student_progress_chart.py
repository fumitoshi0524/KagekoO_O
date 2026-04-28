"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        student_id = data.get('student_id')
        course_name = data.get('course_name')
        assessments = data.get('assessments')
        if not student_id or not course_name or not assessments:
            return 'error: missing required fields'
        if not isinstance(assessments, list) or len(assessments) == 0:
            return 'error: assessments must be a non-empty list'
        for item in assessments:
            if not all(k in item for k in ('assessment_name', 'score', 'date')):
                return 'error: each assessment must have assessment_name, score, and date'
            if not isinstance(item['score'], (int, float)) or item['score'] < 0 or item['score'] > 100:
                return 'error: score must be between 0 and 100'
        
        # Generate SVG line chart
        chart_title = data.get('chart_title', f'Student Progress: {course_name}')
        width = min(max(data.get('chart_width', 800), 400), 1200)
        height = min(max(data.get('chart_height', 500), 300), 800)
        
        # Simple SVG generation
        padding = 50
        plot_width = width - 2 * padding
        plot_height = height - 2 * padding
        
        points_x = []
        points_y = []
        labels_x = []
        labels_y_vals = []
        for i, a in enumerate(assessments):
            x = padding + (i / max(len(assessments) - 1, 1)) * plot_width
            y = padding + plot_height - (a['score'] / 100.0) * plot_height
            points_x.append(round(x, 2))
            points_y.append(round(y, 2))
            labels_x.append(a['assessment_name'])
            labels_y_vals.append(a['score'])
        
        polyline_points = ' '.join(f'{x},{y}' for x, y in zip(points_x, points_y))
        
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        svg += f'<rect width="{width}" height="{height}" fill="white" />'
        svg += f'<text x="{width/2}" y="20" text-anchor="middle" font-size="16" font-weight="bold">{chart_title}</text>'
        svg += f'<polyline points="{polyline_points}" fill="none" stroke="steelblue" stroke-width="2" />'
        for x, y, label, val in zip(points_x, points_y, labels_x, labels_y_vals):
            svg += f'<circle cx="{x}" cy="{y}" r="4" fill="steelblue" />'
            svg += f'<text x="{x}" y="{y - 10}" text-anchor="middle" font-size="10">{val}</text>'
            svg += f'<text x="{x}" y="{height - 5}" text-anchor="middle" font-size="10" transform="rotate(-20, {x}, {height-5})">{label}</text>'
        svg += '</svg>'
        
        result = {
            'student_id': student_id,
            'course_name': course_name,
            'number_of_assessments': len(assessments),
            'average_score': round(sum(a['score'] for a in assessments) / len(assessments), 2),
            'highest_score': max(a['score'] for a in assessments),
            'lowest_score': min(a['score'] for a in assessments),
            'chart_svg': svg
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "student_progress_chart",
    "description": "Generates a line chart visualization of a student's academic progress over time, showing scores or grades across multiple assessments or courses, useful for educators and students to track performance trends.",
    "category": "visualization",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "student_id": {
            "type": "string",
            "description": "Unique identifier for the student whose progress is being charted."
        },
        "course_name": {
            "type": "string",
            "description": "Name of the course or subject for which progress is tracked."
        },
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "assessment_name": {
                        "type": "string",
                        "description": "Name or label of the assessment (e.g., 'Quiz 1', 'Midterm Exam')."
                    },
                    "score": {
                        "type": "number",
                        "description": "Numeric score or grade achieved (0-100 scale)."
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the assessment in YYYY-MM-DD format."
                    }
                },
                "required": [
                    "assessment_name",
                    "score",
                    "date"
                ]
            },
            "description": "List of assessments with their scores and dates for the chart."
        },
        "chart_title": {
            "type": "string",
            "description": "Optional: Custom title for the chart. Defaults to 'Student Progress: [course_name]'."
        },
        "chart_width": {
            "type": "integer",
            "description": "Optional: Width of the chart in pixels (min 400, max 1200). Default 800."
        },
        "chart_height": {
            "type": "integer",
            "description": "Optional: Height of the chart in pixels (min 300, max 800). Default 500."
        }
    },
    "required": [
        "student_id",
        "course_name",
        "assessments"
    ]
},
}
