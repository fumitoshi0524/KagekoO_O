"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze course titles against keywords to produce a relevance matrix."""
    import json
    try:
        data = json.loads(payload)
        courses = data.get('courses', [])
        keywords = data.get('keywords', [])
        if not courses or not keywords:
            return json.dumps({'error': 'Both courses and keywords must be non-empty lists.'}, ensure_ascii=False)
        results = []
        for course in courses:
            course_lower = course.lower()
            matches = []
            for kw in keywords:
                if kw.lower() in course_lower:
                    matches.append(kw)
            results.append({
                'course': course,
                'matched_keywords': matches,
                'relevance_score': round(len(matches) / len(keywords), 4)
            })
        summary = {
            'total_courses': len(courses),
            'total_keywords': len(keywords),
            'course_analyses': results
        }
        return json.dumps(summary, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "curriculum_relevance_matrix",
    "description": "Analyze a set of academic course titles against a list of industry or domain keywords to produce a relevance score matrix, identifying which courses best align with specific skill areas or job roles.",
    "category": "analysis",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "courses": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Array of course or training program titles to be analyzed for relevance."
        },
        "keywords": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Array of domain-specific keywords, skill names, or job role terms to match against course titles."
        }
    },
    "required": [
        "courses",
        "keywords"
    ]
},
}
