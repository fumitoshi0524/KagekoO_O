"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for academic courses by code, title, instructor, or department."""
    import json
    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        if not query:
            return json.dumps({'error': 'query parameter is required and cannot be empty'}, ensure_ascii=False)
        department = data.get('department', '').strip()
        max_results = data.get('max_results', 20)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 100:
            return json.dumps({'error': 'max_results must be an integer between 1 and 100'}, ensure_ascii=False)
        
        # Simulated course database
        courses = [
            {'code': 'CS101', 'title': 'Introduction to Computer Science', 'instructor': 'Dr. Alan Turing', 'department': 'Computer Science', 'credits': 4, 'prerequisites': [], 'schedule': 'Mon/Wed 10:00-11:30'},
            {'code': 'MATH201', 'title': 'Calculus II', 'instructor': 'Prof. Isaac Newton', 'department': 'Mathematics', 'credits': 4, 'prerequisites': ['MATH101'], 'schedule': 'Tue/Thu 9:00-10:30'},
            {'code': 'ENG110', 'title': 'English Composition', 'instructor': 'Dr. Jane Austen', 'department': 'English', 'credits': 3, 'prerequisites': [], 'schedule': 'Mon/Wed/Fri 11:00-12:00'},
            {'code': 'HIST200', 'title': 'World History Since 1500', 'instructor': 'Prof. Herodotus', 'department': 'History', 'credits': 3, 'prerequisites': [], 'schedule': 'Tue/Thu 14:00-15:30'},
            {'code': 'PHYS101', 'title': 'Introduction to Physics', 'instructor': 'Dr. Marie Curie', 'department': 'Physics', 'credits': 4, 'prerequisites': ['MATH101'], 'schedule': 'Mon/Wed 14:00-15:30'},
            {'code': 'CS205', 'title': 'Data Structures', 'instructor': 'Dr. Ada Lovelace', 'department': 'Computer Science', 'credits': 4, 'prerequisites': ['CS101'], 'schedule': 'Tue/Thu 10:30-12:00'},
            {'code': 'MATH301', 'title': 'Linear Algebra', 'instructor': 'Prof. Emmy Noether', 'department': 'Mathematics', 'credits': 3, 'prerequisites': ['MATH201'], 'schedule': 'Mon/Wed/Fri 9:00-10:00'},
            {'code': 'BIO101', 'title': 'Biology Basics', 'instructor': 'Dr. Charles Darwin', 'department': 'Biology', 'credits': 4, 'prerequisites': [], 'schedule': 'Tue/Thu 13:00-14:30'}
        ]
        
        # Perform search (case-insensitive matching)
        query_lower = query.lower()
        results = []
        for c in courses:
            if query_lower in c['code'].lower() or query_lower in c['title'].lower() or query_lower in c['instructor'].lower():
                if department and c['department'].lower() != department.lower():
                    continue
                results.append(c)
            elif query_lower in c['department'].lower() and not department:
                results.append(c)
        
        # Sort by code for consistent ordering, limit results
        results.sort(key=lambda x: x['code'])
        results = results[:max_results]
        
        return json.dumps({'results': results, 'total_matches': len(results), 'query': query}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Failed to process request: {str(e)}'}, ensure_ascii=False)



TOOL_SPEC = {
    "name": "course_lookup",
    "description": "Search for academic courses by course code, title, instructor, or department, returning matching course records with descriptions, prerequisites, credits, and schedule information.",
    "category": "search",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search term to match against course code, title, or instructor name. Supports partial and fuzzy matching."
        },
        "department": {
            "type": "string",
            "description": "Optional: Filter results to a specific academic department (e.g., Computer Science, Mathematics, History). If omitted, search across all departments."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of course results to return. Must be between 1 and 100. Defaults to 20.",
            "minimum": 1,
            "maximum": 100,
            "default": 20
        }
    },
    "required": [
        "query"
    ]
},
}
