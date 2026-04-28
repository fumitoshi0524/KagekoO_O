"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        course = data.get('course_name')
        student_id = data.get('student_id')
        assignments = data.get('assignments')
        if not course or not student_id or not assignments:
            return json.dumps({'error': 'Missing required fields: course_name, student_id, assignments'})
        if len(assignments) == 0:
            return json.dumps({'error': 'Assignments list must not be empty'})
        # Collect all categories from assignments
        categories = {}
        for a in assignments:
            cat = a.get('weight_category', 'General')
            if cat not in categories:
                categories[cat] = {'total_score': 0.0, 'total_max': 0.0, 'count': 0}
            score = a['score']
            max_score = a['max_score']
            if max_score <= 0:
                return json.dumps({'error': 'max_score must be positive'})
            categories[cat]['total_score'] += score
            categories[cat]['total_max'] += max_score
            categories[cat]['count'] += 1
        # Build weight configuration
        weight_config = data.get('weight_config', {})
        # Assign default equal weights if none provided
        if not weight_config:
            equal_weight = 1.0 / len(categories)
            for cat in categories:
                weight_config[cat] = equal_weight
        else:
            # Validate weights sum to 1.0 (approximately)
            total_weight = sum(weight_config.values())
            if abs(total_weight - 1.0) > 0.01:
                return json.dumps({'error': 'Weight config must sum to 1.0 (within 0.01 tolerance)'})
            # Check all categories present
            for cat in categories:
                if cat not in weight_config:
                    return json.dumps({'error': f'Missing weight for category: {cat}'})
        # Compute weighted grade
        weighted_sum = 0.0
        for cat, info in categories.items():
            if info['total_max'] == 0:
                continue
            percentage = info['total_score'] / info['total_max'] * 100
            weighted_sum += percentage * weight_config[cat]
        final_percentage = round(weighted_sum, 2)
        # Letter grade mapping (common US scale)
        if final_percentage >= 90:
            letter = 'A'
        elif final_percentage >= 80:
            letter = 'B'
        elif final_percentage >= 70:
            letter = 'C'
        elif final_percentage >= 60:
            letter = 'D'
        else:
            letter = 'F'
        # GPA scale (4.0)
        gpa = round(4.0 * final_percentage / 100, 2)
        if gpa > 4.0:
            gpa = 4.0
        # Compute class ranking if classmates_scores provided
        ranking = None
        classmates = data.get('classmates_scores')
        if classmates is not None:
            all_scores = classmates + [final_percentage]
            all_scores_sorted = sorted(all_scores, reverse=True)
            rank = all_scores_sorted.index(final_percentage) + 1
            total = len(all_scores_sorted)
            percentile = round((total - rank) / total * 100, 1) if total > 1 else 100.0
            ranking = {'rank': rank, 'total_students': total, 'percentile': percentile}
        # Category breakdown
        breakdown = {}
        for cat, info in categories.items():
            if info['total_max'] > 0:
                pct = round(info['total_score'] / info['total_max'] * 100, 2)
            else:
                pct = 0.0
            breakdown[cat] = {
                'total_score': info['total_score'],
                'total_max': info['total_max'],
                'percentage': pct
            }
        result = {
            'course_name': course,
            'student_id': student_id,
            'final_percentage': final_percentage,
            'letter_grade': letter,
            'gpa': gpa,
            'category_breakdown': breakdown,
            'ranking': ranking
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "student_gradebook",
    "description": "Manage student grade entries, compute weighted final grades, and generate a grade summary report including letter grades, GPA, and class ranking within an educational course or program.",
    "category": "operations",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "course_name": {
            "type": "string",
            "description": "Name of the course or subject for which grades are being processed."
        },
        "student_id": {
            "type": "string",
            "description": "Unique identifier for the student (alphanumeric)."
        },
        "assignments": {
            "type": "array",
            "description": "List of assignment entries with scores and weight categories.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Assignment name (e.g., 'Midterm Exam')."
                    },
                    "score": {
                        "type": "number",
                        "description": "Numeric score achieved by the student (0-100)."
                    },
                    "max_score": {
                        "type": "number",
                        "description": "Maximum possible score for the assignment."
                    },
                    "weight_category": {
                        "type": "string",
                        "description": "Category for weighting (e.g., 'Homework', 'Quiz', 'Exam', 'Project')."
                    }
                },
                "required": [
                    "name",
                    "score",
                    "max_score",
                    "weight_category"
                ]
            }
        },
        "weight_config": {
            "type": "object",
            "description": "Optional: Dictionary mapping weight category names to their percentage weights (e.g., Homework: 0.2). Default weights are equal distribution among categories.",
            "additionalProperties": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            }
        },
        "classmates_scores": {
            "type": "array",
            "description": "Optional: List of total scores (numeric) of other students in the same course to compute class ranking. If omitted, no ranking is returned.",
            "items": {
                "type": "number"
            }
        }
    },
    "required": [
        "course_name",
        "student_id",
        "assignments"
    ]
},
}
