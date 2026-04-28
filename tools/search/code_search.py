"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import re
    import os
    import random

    try:
        data = json.loads(payload)
        query = data.get('query')
        search_type = data.get('search_type')
        scope = data.get('scope', 'file')
        context_lines = data.get('context_lines', 2)
        case_sensitive = data.get('case_sensitive', False)

        if not query or not search_type:
            return json.dumps({'error': 'Missing required fields: query and search_type'})
        if search_type not in ['keyword', 'regex']:
            return json.dumps({'error': 'search_type must be keyword or regex'})
        if scope not in ['function', 'file']:
            return json.dumps({'error': 'scope must be function or file'})
        if not isinstance(context_lines, int) or context_lines < 0 or context_lines > 10:
            return json.dumps({'error': 'context_lines must be integer between 0 and 10'})

        # Simulated repository of code snippets
        repo = {
            'utils.py': {
                'content': [
                    'import math',
                    '',
                    'def calculate_factorial(n):',
                    '    """Return factorial of n."""',
                    '    return math.factorial(n)',
                    '',
                    'def is_prime(number):',
                    '    """Check if number is prime."""',
                    '    if number < 2:',
                    '        return False',
                    '    for i in range(2, int(number**0.5)+1):',
                    '        if number % i == 0:',
                    '            return False',
                    '    return True'
                ],
                'functions': {
                    'calculate_factorial': {'start': 2, 'end': 4},
                    'is_prime': {'start': 6, 'end': 12}
                }
            },
            'app.py': {
                'content': [
                    'from flask import Flask',
                    'app = Flask(__name__)',
                    '',
                    '@app.route("/")',
                    'def home():',
                    '    return "Hello World"',
                    '',
                    '@app.route("/user/<name>")',
                    'def greet_user(name):',
                    '    return f"Hello {name}"'
                ],
                'functions': {
                    'home': {'start': 4, 'end': 5},
                    'greet_user': {'start': 8, 'end': 9}
                }
            }
        }

        results = []

        for filename, file_data in repo.items():
            lines = file_data['content']
            if scope == 'function':
                search_areas = []
                for func_name, boundaries in file_data['functions'].items():
                    search_areas.append((func_name, boundaries['start'], boundaries['end']))
            else:
                search_areas = [('full_file', 0, len(lines)-1)]

            for area_name, start_line, end_line in search_areas:
                for line_no in range(start_line, end_line+1):
                    line = lines[line_no]
                    if not case_sensitive:
                        line_lower = line.lower()
                        query_lower = query.lower()
                    else:
                        line_lower = line
                        query_lower = query

                    if search_type == 'keyword':
                        if query_lower in line_lower:
                            match = True
                        else:
                            match = False
                    else:  # regex
                        try:
                            flags = 0 if case_sensitive else re.IGNORECASE
                            if re.search(query, line, flags):
                                match = True
                            else:
                                match = False
                        except re.error:
                            return json.dumps({'error': 'Invalid regex pattern'})

                    if match:
                        context_start = max(0, line_no - context_lines)
                        context_end = min(len(lines)-1, line_no + context_lines)
                        context = '\n'.join(lines[context_start:context_end+1])
                        results.append({
                            'file': filename,
                            'scope': area_name,
                            'line': line_no + 1,
                            'matched_line': line,
                            'context': context
                        })
                        break  # avoid duplicate matches in same scope

        if not results:
            return json.dumps({'results': [], 'total': 0, 'message': 'No matches found'})

        # Sort results by file and line number
        results.sort(key=lambda x: (x['file'], x['line']))
        return json.dumps({'results': results, 'total': len(results)}, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "code_search",
    "description": "Search through a repository of code snippets or function definitions by keyword or regex pattern, returning matching results with file name, line number, and surrounding context.",
    "category": "search",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search term or pattern to match against code contents."
        },
        "search_type": {
            "type": "string",
            "description": "Type of search: 'keyword' for literal keyword matching, 'regex' for regular expression pattern matching.",
            "enum": [
                "keyword",
                "regex"
            ]
        },
        "scope": {
            "type": "string",
            "description": "Optional: Scope of search. 'function' to search only function definitions, 'file' to search entire file contents. Default is 'file'.",
            "enum": [
                "function",
                "file"
            ]
        },
        "context_lines": {
            "type": "integer",
            "description": "Optional: Number of surrounding lines to include before and after each match. Must be between 0 and 10. Default is 2."
        },
        "case_sensitive": {
            "type": "boolean",
            "description": "Optional: Whether the search is case-sensitive. Default is False."
        }
    },
    "required": [
        "query",
        "search_type"
    ]
},
}
