"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query')
        if not query or not isinstance(query, str) or not query.strip():
            return json.dumps({'error': 'Missing required parameter: query'}, ensure_ascii=False)
        education_level = data.get('education_level', 'all')
        subject_area = data.get('subject_area')
        max_results = data.get('max_results', 10)
        sort_by = data.get('sort_by', 'relevance')
        if not isinstance(max_results, int) or max_results < 1:
            max_results = 10
        if max_results > 50:
            max_results = 50
        valid_levels = ['undergraduate', 'graduate', 'high_school', 'vocational', 'all']
        if education_level not in valid_levels:
            education_level = 'all'
        valid_sorts = ['relevance', 'title_asc', 'title_desc', 'credits_asc', 'credits_desc']
        if sort_by not in valid_sorts:
            sort_by = 'relevance'

        # Simulated course database (in production, this would query a real index)
        course_db = [
            {'course_code': 'CS101', 'title': 'Introduction to Computer Science', 'description': 'Basic programming, algorithms, and data structures.', 'credits': 4, 'level': 'undergraduate', 'subject': 'Computer Science', 'prerequisites': []},
            {'course_code': 'CS201', 'title': 'Data Structures and Algorithms', 'description': 'Advanced data structures and algorithm analysis.', 'credits': 4, 'level': 'undergraduate', 'subject': 'Computer Science', 'prerequisites': ['CS101']},
            {'course_code': 'MATH101', 'title': 'Calculus I', 'description': 'Limits, derivatives, integrals, and applications.', 'credits': 4, 'level': 'undergraduate', 'subject': 'Mathematics', 'prerequisites': []},
            {'course_code': 'PHY101', 'title': 'Physics for Scientists and Engineers I', 'description': 'Mechanics, thermodynamics, waves.', 'credits': 4, 'level': 'undergraduate', 'subject': 'Physics', 'prerequisites': ['MATH101']},
            {'course_code': 'GRAD_ML', 'title': 'Machine Learning', 'description': 'Supervised and unsupervised learning, neural networks.', 'credits': 3, 'level': 'graduate', 'subject': 'Computer Science', 'prerequisites': ['CS201']},
            {'course_code': 'GRAD_DL', 'title': 'Deep Learning', 'description': 'Convolutional and recurrent networks, transformers.', 'credits': 3, 'level': 'graduate', 'subject': 'Computer Science', 'prerequisites': ['GRAD_ML']},
            {'course_code': 'ART101', 'title': 'Introduction to Art History', 'description': 'Survey of Western art from Renaissance to modern.', 'credits': 3, 'level': 'undergraduate', 'subject': 'Art History', 'prerequisites': []},
            {'course_code': 'VOC_WELD', 'title': 'Welding Fundamentals', 'description': 'Basic welding techniques and safety procedures.', 'credits': 6, 'level': 'vocational', 'subject': 'Trades', 'prerequisites': []},
            {'course_code': 'HS_SCI', 'title': 'High School Biology', 'description': 'Cell biology, genetics, ecology.', 'credits': 1, 'level': 'high_school', 'subject': 'Biology', 'prerequisites': []},
            {'course_code': 'HS_MATH', 'title': 'High School Algebra', 'description': 'Linear equations, functions, polynomials.', 'credits': 1, 'level': 'high_school', 'subject': 'Mathematics', 'prerequisites': []},
        ]

        # Filter by education level
        if education_level != 'all':
            course_db = [c for c in course_db if c['level'] == education_level]

        # Filter by subject area
        if subject_area:
            subject_lower = subject_area.lower()
            course_db = [c for c in course_db if subject_lower in c['subject'].lower()]

        # Search query matching on title, description, and subject (simple keyword search)
        query_lower = query.strip().lower()
        results = []
        for course in course_db:
            score = 0
            if query_lower in course['title'].lower():
                score += 10
            if query_lower in course['description'].lower():
                score += 5
            if query_lower in course['subject'].lower():
                score += 3
            if query_lower in course['course_code'].lower():
                score += 2
            if query_lower in ' '.join(course['prerequisites']).lower():
                score += 1
            if score > 0:
                results.append((course, score))

        # Sort by score or other criteria
        if sort_by == 'relevance':
            results.sort(key=lambda x: x[1], reverse=True)
        elif sort_by == 'title_asc':
            results.sort(key=lambda x: x[0]['title'].lower())
        elif sort_by == 'title_desc':
            results.sort(key=lambda x: x[0]['title'].lower(), reverse=True)
        elif sort_by == 'credits_asc':
            results.sort(key=lambda x: x[0]['credits'])
        elif sort_by == 'credits_desc':
            results.sort(key=lambda x: x[0]['credits'], reverse=True)

        # Limit results
        results = results[:max_results]

        output_courses = [
            {
                'course_code': course['course_code'],
                'title': course['title'],
                'description': course['description'],
                'credits': course['credits'],
                'level': course['level'],
                'subject': course['subject'],
                'prerequisites': course['prerequisites']
            }
            for course, _ in results
        ]

        return json.dumps({'courses': output_courses, 'total': len(output_courses)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "course_search",
    "description": "Search for academic courses across multiple education levels and subjects, returning structured results including course codes, titles, descriptions, prerequisites, and credit hours to help learners find suitable educational offerings.",
    "category": "search",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Natural language search term for courses, e.g., 'machine learning' or 'introduction to psychology'."
        },
        "education_level": {
            "type": "string",
            "enum": [
                "undergraduate",
                "graduate",
                "high_school",
                "vocational",
                "all"
            ],
            "description": "Filter courses by education level. Use 'all' to include every level."
        },
        "subject_area": {
            "type": "string",
            "description": "Optional: Restrict search to a specific academic subject or department (e.g., 'Computer Science', 'Art History')."
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "description": "Optional: Maximum number of course results to return. Default is 10."
        },
        "sort_by": {
            "type": "string",
            "enum": [
                "relevance",
                "title_asc",
                "title_desc",
                "credits_asc",
                "credits_desc"
            ],
            "description": "Optional: Sort order for results. Default is 'relevance'."
        }
    },
    "required": [
        "query"
    ]
},
}
