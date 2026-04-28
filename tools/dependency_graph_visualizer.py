"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a directed graph visualization of software package dependencies showing relationships between modules, libraries, or components."""
    import json
    try:
        data = json.loads(payload)
        packages = data.get('packages', [])
        dependencies = data.get('dependencies', [])
        layout = data.get('layout', 'hierarchical')
        highlight_circular = data.get('highlight_circular', False)
        max_depth = data.get('max_depth', 3)
        
        if not packages:
            return json.dumps({'error': 'At least one package is required'}, ensure_ascii=False)
        if not dependencies:
            return json.dumps({'error': 'At least one dependency relationship is required'}, ensure_ascii=False)
        
        # Validate packages and dependencies exist
        package_names = {p['name'] for p in packages}
        for dep in dependencies:
            if dep['from'] not in package_names:
                return json.dumps({'error': f"Package '{dep['from']}' not found in packages list"}, ensure_ascii=False)
            if dep['to'] not in package_names:
                return json.dumps({'error': f"Package '{dep['to']}' not found in packages list"}, ensure_ascii=False)
        
        # Build graph structure
        nodes = []
        for pkg in packages:
            node = {
                'id': pkg['name'],
                'label': pkg['name'],
                'version': pkg.get('version', 'unknown'),
                'in_degree': 0,
                'out_degree': 0,
                'dependencies': []
            }
            nodes.append(node)
        
        # Map node ids to indices
        node_map = {n['id']: idx for idx, n in enumerate(nodes)}
        
        edges = []
        edge_map = {}  # Track unique edges
        for dep in dependencies:
            edge_key = (dep['from'], dep['to'])
            if edge_key in edge_map:
                edge_map[edge_key]['types'].append(dep.get('type', 'runtime'))
                continue
            
            edge = {
                'source': dep['from'],
                'target': dep['to'],
                'types': [dep.get('type', 'runtime')],
                'is_circular': False
            }
            edges.append(edge)
            edge_map[edge_key] = edge
            
            # Update degrees
            src_idx = node_map[dep['from']]
            tgt_idx = node_map[dep['to']]
            nodes[src_idx]['out_degree'] += 1
            nodes[tgt_idx]['in_degree'] += 1
            nodes[src_idx]['dependencies'].append(dep['to'])
        
        # Detect circular dependencies using DFS
        if highlight_circular:
            def dfs_find_cycles(start_node, current_path, visited):
                cycles = []
                current_node = current_path[-1]
                for neighbor in nodes[node_map[current_node]]['dependencies']:
                    if neighbor == start_node and len(current_path) > 1:
                        cycles.append(list(current_path))
                    elif neighbor not in visited:
                        visited.add(neighbor)
                        new_path = current_path + [neighbor]
                        result = dfs_find_cycles(start_node, new_path, visited)
                        cycles.extend(result)
                return cycles
            
            all_cycles = set()
            for pkg in packages:
                cycles = dfs_find_cycles(pkg['name'], [pkg['name']], {pkg['name']})
                for cycle in cycles:
                    all_cycles.add(tuple(cycle))
            
            # Mark edges in cycles
            for cycle in all_cycles:
                for i in range(len(cycle)):
                    src = cycle[i]
                    tgt = cycle[(i + 1) % len(cycle)]
                    if (src, tgt) in edge_map:
                        edge_map[(src, tgt)]['is_circular'] = True
        
        # Build hierarchical layout if requested
        if layout == 'hierarchical':
            # Compute levels using topological sort (but handle cycles gracefully)
            levels = {}
            for pkg in packages:
                name = pkg['name']
                depth = 0
                # Follow dependencies up to max_depth
                current = name
                visited = set()
                level = 0
                while current in node_map and level < max_depth:
                    visited.add(current)
                    deps = nodes[node_map[current]]['dependencies']
                    if not deps:
                        break
                    # Pick first unvisited or first dependency
                    next_pkg = None
                    for dep in deps:
                        # Check for circular
                        if dep not in visited:
                            next_pkg = dep
                            break
                    if next_pkg is None:
                        next_pkg = deps[0]  # fallback to first dep
                    current = next_pkg
                    level += 1
                levels[name] = level
            for node in nodes:
                node['level'] = levels.get(node['id'], 0)
        
        result = {
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'total_packages': len(nodes),
                'total_dependencies': len(edges),
                'layout': layout,
                'max_depth': max_depth,
                'has_circular_dependencies': any(e['is_circular'] for e in edges)
            }
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "dependency_graph_visualizer",
    "description": "Generate a directed graph visualization of software package dependencies showing relationships between modules, libraries, or components, returning nodes (packages with version/status) and edges (dependency relationships with types) for use in system architecture review and dependency analysis.",
    "category": "visualization",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "packages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the package or module"
                    },
                    "version": {
                        "type": "string",
                        "description": "Version identifier of the package"
                    }
                },
                "required": [
                    "name"
                ]
            },
            "description": "List of packages/modules to include in the dependency graph"
        },
        "dependencies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {
                        "type": "string",
                        "description": "Name of the dependent package (source node)"
                    },
                    "to": {
                        "type": "string",
                        "description": "Name of the dependency package (target node)"
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "runtime",
                            "dev",
                            "optional",
                            "peer"
                        ],
                        "description": "Dependency relationship type"
                    }
                },
                "required": [
                    "from",
                    "to"
                ]
            },
            "description": "List of dependency relationships between packages"
        },
        "layout": {
            "type": "string",
            "enum": [
                "hierarchical",
                "circular",
                "force_directed",
                "radial"
            ],
            "description": "Optional: Graph layout algorithm for node positioning. Default is hierarchical."
        },
        "highlight_circular": {
            "type": "boolean",
            "description": "Optional: Whether to highlight circular dependencies in the output. Default is false."
        },
        "max_depth": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Optional: Maximum depth of dependency traversal (for hierarchical layouts). Default is 3."
        }
    },
    "required": [
        "packages",
        "dependencies"
    ]
},
}
