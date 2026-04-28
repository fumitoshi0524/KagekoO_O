"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query')
        if not query or not isinstance(query, str) or len(query.strip()) == 0:
            return json.dumps({'error': 'query parameter must be a non-empty string'})
        query = query.lower().strip()
        level = data.get('level', 'all')
        provider = data.get('provider', '')
        max_results = data.get('max_results', 20)
        sort_by = data.get('sort_by', 'relevance')
        if max_results is not None:
            try:
                max_results = int(max_results)
            except (ValueError, TypeError):
                max_results = 20
            if max_results < 1 or max_results > 50:
                max_results = 20
        if level not in ['undergraduate', 'graduate', 'certificate', 'professional', 'all']:
            level = 'all'
        if sort_by not in ['relevance', 'title', 'provider']:
            sort_by = 'relevance'
        # Simulated course database
        courses = [
            {'id': 'CS101', 'title': 'Introduction to Computer Science', 'description': 'Fundamentals of programming, algorithms, and data structures for undergraduates.', 'level': 'undergraduate', 'provider': 'MIT', 'credits': 4, 'url': 'https://mit.edu/courses/cs101'},
            {'id': 'ML201', 'title': 'Machine Learning Foundations', 'description': 'Supervised and unsupervised learning, neural networks, and model evaluation.', 'level': 'graduate', 'provider': 'Stanford', 'credits': 3, 'url': 'https://stanford.edu/courses/ml201'},
            {'id': 'AH101', 'title': 'Art History: Renaissance to Modern', 'description': 'Survey of Western art from the Renaissance through contemporary movements.', 'level': 'undergraduate', 'provider': 'Harvard', 'credits': 3, 'url': 'https://harvard.edu/courses/ah101'},
            {'id': 'BIO202', 'title': 'Molecular Biology', 'description': 'Advanced study of cellular processes, genetics, and biotechnology.', 'level': 'graduate', 'provider': 'MIT', 'credits': 4, 'url': 'https://mit.edu/courses/bio202'},
            {'id': 'PM101', 'title': 'Project Management Professional', 'description': 'Certification prep covering PMBOK, Agile, and Scrum methodologies.', 'level': 'professional', 'provider': 'Coursera', 'credits': 2, 'url': 'https://coursera.org/courses/pm101'},
            {'id': 'DS201', 'title': 'Data Science with Python', 'description': 'Practical data analysis, visualization, and machine learning using Python libraries.', 'level': 'graduate', 'provider': 'Coursera', 'credits': 3, 'url': 'https://coursera.org/courses/ds201'},
            {'id': 'PHY101', 'title': 'Physics for Engineers', 'description': 'Mechanics, electromagnetism, and thermodynamics with calculus-based approach.', 'level': 'undergraduate', 'provider': 'MIT', 'credits': 4, 'url': 'https://mit.edu/courses/phy101'},
            {'id': 'WS101', 'title': 'Writing and Communication Skills', 'description': 'Develop clear academic writing and presentation skills for professional contexts.', 'level': 'undergraduate', 'provider': 'Harvard', 'credits': 2, 'url': 'https://harvard.edu/courses/ws101'},
            {'id': 'AI401', 'title': 'Advanced Artificial Intelligence', 'description': 'Deep learning, reinforcement learning, and natural language processing for PhD students.', 'level': 'graduate', 'provider': 'Stanford', 'credits': 4, 'url': 'https://stanford.edu/courses/ai401'},
            {'id': 'CE101', 'title': 'Civil Engineering Principles', 'description': 'Structural analysis, geotechnical engineering, and design fundamentals.', 'level': 'undergraduate', 'provider': 'MIT', 'credits': 3, 'url': 'https://mit.edu/courses/ce101'},
            {'id': 'MGMT301', 'title': 'Strategic Management', 'description': 'Business strategy, competitive analysis, and organizational leadership.', 'level': 'graduate', 'provider': 'Harvard', 'credits': 3, 'url': 'https://harvard.edu/courses/mgmt301'},
            {'id': 'CERT01', 'title': 'Cloud Computing Certification', 'description': 'AWS, Azure, and Google Cloud fundamentals for IT professionals.', 'level': 'certificate', 'provider': 'Coursera', 'credits': 1, 'url': 'https://coursera.org/courses/cert01'},
            {'id': 'MUS101', 'title': 'Music Theory and Composition', 'description': 'Reading music, harmony, and basic composition techniques.', 'level': 'undergraduate', 'provider': 'Harvard', 'credits': 3, 'url': 'https://harvard.edu/courses/mus101'},
            {'id': 'PSY101', 'title': 'Introduction to Psychology', 'description': 'Cognitive, developmental, and social psychology principles.', 'level': 'undergraduate', 'provider': 'Stanford', 'credits': 3, 'url': 'https://stanford.edu/courses/psy101'}
        ]
        # Filter by query
        results = []
        for c in courses:
            query_lower = query.lower()
            match_title = query_lower in c['title'].lower()
            match_desc = query_lower in c['description'].lower()
            if match_title or match_desc:
                results.append(c)
        if level != 'all':
            results = [c for c in results if c['level'] == level]
        if provider:
            provider_lower = provider.lower()
            results = [c for c in results if provider_lower in c['provider'].lower()]
        # Sort
        if sort_by == 'title':
            results.sort(key=lambda x: x['title'])
        elif sort_by == 'provider':
            results.sort(key=lambda x: x['provider'])
        else:
            # relevance: keep original order (already matched)
            pass
        results = results[:max_results]
        return json.dumps({
            'count': len(results),
            'courses': [{
                'id': c['id'],
                'title': c['title'],
                'description': c['description'],
                'level': c['level'],
                'provider': c['provider'],
                'credits': c['credits'],
                'url': c['url']
            } for c in results]
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Internal error: {str(e)}'})


TOOL_SPEC = {
    "name": "course_finder",
    "description": "Search for academic courses across multiple disciplines by keyword, level, and provider, returning course titles, descriptions, credit hours, and enrollment links for use in curriculum planning and student advising.",
    "category": "search",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Keyword or phrase to search for matching course titles and descriptions (e.g., 'machine learning', 'renaissance art')"
        },
        "level": {
            "type": "string",
            "description": "Optional: Filter courses by education level. Allowed values: undergraduate, graduate, certificate, professional, all",
            "enum": [
                "undergraduate",
                "graduate",
                "certificate",
                "professional",
                "all"
            ]
        },
        "provider": {
            "type": "string",
            "description": "Optional: Filter by institution or platform name (e.g., 'MIT', 'Coursera', 'Harvard'). Case-insensitive partial match."
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of course results to return. Must be between 1 and 50. Default is 20."
        },
        "sort_by": {
            "type": "string",
            "description": "Optional: Sort order of results. Allowed values: relevance, title, provider",
            "enum": [
                "relevance",
                "title",
                "provider"
            ]
        }
    },
    "required": [
        "query"
    ]
},
}
