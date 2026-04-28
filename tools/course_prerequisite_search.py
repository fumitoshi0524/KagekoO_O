"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for academic course prerequisites and dependencies across a curriculum."""
    import json
    try:
        data = json.loads(payload)
        course_code = data.get('course_code', '').strip().upper()
        search_mode = data.get('search_mode', 'direct')
        include_descriptions = data.get('include_descriptions', False)
        max_depth = data.get('max_depth', 5)

        if not course_code:
            return json.dumps({'error': 'Course code is required'})

        # Simulated course catalog with prerequisites (real system would query DB)
        course_catalog = {
            'CS101': {
                'title': 'Introduction to Computer Science',
                'description': 'Fundamentals of programming and computational thinking',
                'prerequisites': [],
                'corequisites': []
            },
            'CS201': {
                'title': 'Data Structures',
                'description': 'Abstract data types, algorithms, and complexity analysis',
                'prerequisites': ['CS101'],
                'corequisites': ['MATH101']
            },
            'CS301': {
                'title': 'Algorithms',
                'description': 'Design and analysis of algorithms',
                'prerequisites': ['CS201', 'MATH201'],
                'corequisites': []
            },
            'MATH101': {
                'title': 'Calculus I',
                'description': 'Limits, derivatives, and integrals',
                'prerequisites': [],
                'corequisites': []
            },
            'MATH201': {
                'title': 'Calculus II',
                'description': 'Integration techniques, sequences, and series',
                'prerequisites': ['MATH101'],
                'corequisites': []
            },
            'MATH301': {
                'title': 'Linear Algebra',
                'description': 'Vector spaces, matrices, and linear transformations',
                'prerequisites': ['MATH201'],
                'corequisites': []
            }
        }

        if course_code not in course_catalog:
            return json.dumps({'error': f'Course {course_code} not found in catalog'})

        def get_direct_prereqs(code):
            course = course_catalog.get(code)
            if not course:
                return []
            result = []
            for prereq in course.get('prerequisites', []):
                entry = {'code': prereq}
                if include_descriptions and prereq in course_catalog:
                    entry['title'] = course_catalog[prereq]['title']
                    entry['description'] = course_catalog[prereq]['description']
                result.append(entry)
            return result

        def get_prereq_chain(code, depth=0, visited=None):
            if visited is None:
                visited = set()
            if depth > max_depth or code in visited:
                return []
            visited.add(code)
            course = course_catalog.get(code)
            if not course:
                return []
            chain = []
            for prereq in course.get('prerequisites', []):
                entry = {'code': prereq, 'depth': depth + 1}
                if include_descriptions and prereq in course_catalog:
                    entry['title'] = course_catalog[prereq]['title']
                    entry['description'] = course_catalog[prereq]['description']
                children = get_prereq_chain(prereq, depth + 1, visited.copy())
                if children:
                    entry['children'] = children
                chain.append(entry)
            return chain

        def get_corequisites(code):
            course = course_catalog.get(code)
            if not course:
                return []
            result = []
            for coreq in course.get('corequisites', []):
                entry = {'code': coreq}
                if include_descriptions and coreq in course_catalog:
                    entry['title'] = course_catalog[coreq]['title']
                    entry['description'] = course_catalog[coreq]['description']
                result.append(entry)
            return result

        result = {
            'course': {
                'code': course_code,
                'title': course_catalog[course_code]['title']
            },
            'search_mode': search_mode
        }

        if search_mode == 'direct':
            result['prerequisites'] = get_direct_prereqs(course_code)
            result['corequisites'] = get_corequisites(course_code)
            result['has_prerequisites'] = len(result['prerequisites']) > 0
            result['prerequisite_count'] = len(result['prerequisites'])

        elif search_mode == 'full_chain':
            chain = get_prereq_chain(course_code)
            result['prerequisite_chain'] = chain
            result['total_depth'] = max((c.get('depth', 0) for chain_node in chain for c in _flatten_chain(chain_node)), default=0) if chain else 0
            result['unique_prerequisites_count'] = len(set(
                c['code'] for c in _flatten_chain({'children': chain}) if 'code' in c
            )) if chain else 0

        elif search_mode == 'corequisites':
            result['corequisites'] = get_corequisites(course_code)
            result['has_corequisites'] = len(result['corequisites']) > 0
            result['corequisite_count'] = len(result['corequisites'])

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({'error': str(e)})

def _flatten_chain(node):
    """Helper to flatten nested prerequisite chain for counting."""
    items = []
    for child in node.get('children', []):
        items.append(child)
        if 'children' in child:
            items.extend(_flatten_chain(child))
    return items



TOOL_SPEC = {
    "name": "course_prerequisite_search",
    "description": "Search for academic course prerequisites and dependencies across a curriculum, returning prerequisite chains, corequisite requirements, and course dependency graphs for enrollment planning and academic advising.",
    "category": "search",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "course_code": {
            "type": "string",
            "description": "The unique course identifier (e.g., 'CS101', 'MATH201') to search prerequisites for."
        },
        "search_mode": {
            "type": "string",
            "enum": [
                "direct",
                "full_chain",
                "corequisites"
            ],
            "description": "Search depth mode: 'direct' returns immediate prerequisites only, 'full_chain' returns entire prerequisite tree, 'corequisites' returns courses that must be taken concurrently."
        },
        "include_descriptions": {
            "type": "boolean",
            "description": "Optional: Whether to include course title and description for each prerequisite in results. Defaults to false."
        },
        "max_depth": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Optional: Maximum depth of prerequisite chain to traverse when using 'full_chain' mode (default 5)."
        }
    },
    "required": [
        "course_code",
        "search_mode"
    ]
},
}
