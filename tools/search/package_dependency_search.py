"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for package dependencies across multiple package registries."""
    import json
    try:
        data = json.loads(payload)
        
        # Validate required inputs
        if 'package_name' not in data or 'registry' not in data:
            return json.dumps({'error': 'Missing required fields: package_name, registry'}, ensure_ascii=False)
        
        package_name = data['package_name']
        registry = data['registry']
        version = data.get('version', 'latest')
        max_depth = min(max(data.get('max_depth', 2), 1), 5)
        include_licenses = data.get('include_licenses', False)
        
        if registry not in ['npm', 'pypi', 'maven']:
            return json.dumps({'error': f'Unsupported registry: {registry}. Must be npm, pypi, or maven.'}, ensure_ascii=False)
        
        # Simulate dependency resolution (in real implementation would call actual registries)
        # For demonstration, return structured dependency data
        result = {
            'package': package_name,
            'version': version,
            'registry': registry,
            'direct_dependencies': [
                {'name': f'dep1-{package_name}', 'version': '1.0.0', 'vulnerabilities': 0},
                {'name': f'dep2-{package_name}', 'version': '2.1.3', 'vulnerabilities': 1}
            ],
            'transitive_dependencies': [
                {'name': f'trans-dep1', 'version': '0.5.0', 'vulnerabilities': 0},
                {'name': f'trans-dep2', 'version': '3.2.1', 'vulnerabilities': 0}
            ],
            'total_vulnerabilities': 1,
            'dependency_count': 4,
            'max_depth': max_depth
        }
        
        if include_licenses:
            result['licenses'] = {
                'MIT': 2,
                'Apache-2.0': 1,
                'BSD-3-Clause': 1
            }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "package_dependency_search",
    "description": "Search for package dependencies across multiple package registries (npm, PyPI, Maven) by name and version. Returns direct and transitive dependency lists with license information and vulnerability count, used for dependency auditing and license compliance checking.",
    "category": "search",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "package_name": {
            "type": "string",
            "description": "Name of the package to search dependencies for (e.g., 'lodash', 'requests', 'log4j')"
        },
        "registry": {
            "type": "string",
            "enum": [
                "npm",
                "pypi",
                "maven"
            ],
            "description": "Package registry to query: 'npm' (Node.js), 'pypi' (Python), or 'maven' (Java)"
        },
        "version": {
            "type": "string",
            "description": "Specific version of the package to inspect (e.g., '1.2.3'). If omitted, latest stable version is used."
        },
        "max_depth": {
            "type": "integer",
            "description": "Optional: Maximum depth for recursive dependency resolution (1-5). Default is 2."
        },
        "include_licenses": {
            "type": "boolean",
            "description": "Optional: Whether to include license information for each dependency. Default is False."
        }
    },
    "required": [
        "package_name",
        "registry"
    ]
},
}
