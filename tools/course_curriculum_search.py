"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search through academic course curricula and syllabi."""
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip().lower()
        if not query:
            return json.dumps({'error': 'query parameter is required', 'results': []})

        # Mock course database
        courses = [
            {"id": "CS101", "title": "Introduction to Computer Science", "department": "CS", "credits": 4, "level": "undergraduate", "description": "Fundamentals of programming, algorithms, and computational thinking.", "prerequisites": [], "learning_outcomes": ["Write basic programs", "Understand algorithm efficiency"]},
            {"id": "MATH201", "title": "Calculus III", "department": "MATH", "credits": 4, "level": "undergraduate", "description": "Multivariable calculus including partial derivatives, multiple integrals, and vector calculus.", "prerequisites": ["MATH102"], "learning_outcomes": ["Compute partial derivatives", "Evaluate double and triple integrals"]},
            {"id": "ENG450", "title": "Advanced Machine Learning", "department": "ENG", "credits": 3, "level": "graduate", "description": "Deep neural networks, reinforcement learning, and advanced optimization techniques.", "prerequisites": ["CS301", "MATH201"], "learning_outcomes": ["Design neural network architectures", "Implement reinforcement learning algorithms"]},
            {"id": "PHYS101", "title": "Physics for Engineers", "department": "PHYS", "credits": 4, "level": "undergraduate", "description": "Classical mechanics, thermodynamics, and electromagnetism with engineering applications.", "prerequisites": ["MATH101"], "learning_outcomes": ["Apply Newton's laws", "Solve thermodynamics problems"]},
            {"id": "BIO202", "title": "Genetics", "department": "BIO", "credits": 3, "level": "undergraduate", "description": "Principles of inheritance, gene expression, and genomics.", "prerequisites": ["BIO101"], "learning_outcomes": ["Analyze pedigree charts", "Explain DNA replication"]}
        ]

        results = []
        for course in courses:
            # Filter by department
            dept_filter = data.get('department', '').strip().upper()
            if dept_filter and course['department'] != dept_filter:
                continue

            # Filter by level
            level_filter = data.get('level', 'any')
            if level_filter != 'any' and course['level'] != level_filter:
                continue

            # Filter by credit range
            credit_min = data.get('credit_min')
            credit_max = data.get('credit_max')
            if credit_min is not None and course['credits'] < credit_min:
                continue
            if credit_max is not None and course['credits'] > credit_max:
                continue

            # Search query in title, description, and outcomes
            search_text = (course['title'] + ' ' + course['description'] + ' ' + ' '.join(course['learning_outcomes'])).lower()
            if query in search_text:
                results.append(course)

        return json.dumps({'query': data['query'], 'count': len(results), 'results': results}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e), 'results': []})


TOOL_SPEC = {
    "name": "course_curriculum_search",
    "description": "Search through a repository of academic course curricula and syllabi by keyword, department, or credit level, returning matching courses with their description, credit hours, prerequisites, and learning outcomes.",
    "category": "search",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Keyword or phrase to search within course titles, descriptions, and learning outcomes"
        },
        "department": {
            "type": "string",
            "description": "Optional: Filter results by academic department code (e.g., 'CS', 'MATH', 'ENG')"
        },
        "credit_min": {
            "type": "number",
            "description": "Optional: Minimum credit hours filter (1-20)"
        },
        "credit_max": {
            "type": "number",
            "description": "Optional: Maximum credit hours filter (1-20)"
        },
        "level": {
            "type": "string",
            "enum": [
                "undergraduate",
                "graduate",
                "any"
            ],
            "description": "Optional: Course academic level filter. Defaults to 'any'"
        }
    },
    "required": [
        "query"
    ]
},
}
