"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a social network graph from connection data."""
    import json
    from collections import defaultdict

    try:
        data = json.loads(payload)
        connections = data.get('user_connections')
        if not connections or not isinstance(connections, list):
            return json.dumps({'error': 'user_connections must be a non-empty list of connection pairs'})
        
        metadata = data.get('user_metadata', {})
        min_conn = data.get('min_connections', 1)
        centrality = data.get('centrality_metric', 'degree')

        # Build adjacency structure
        adj = defaultdict(set)
        for pair in connections:
            if not isinstance(pair, list) or len(pair) != 2:
                return json.dumps({'error': f'Invalid connection pair: {pair}'})
            u1, u2 = pair[0], pair[1]
            adj[u1].add(u2)
            adj[u2].add(u1)

        # Filter by min_connections
        users_to_keep = {u for u, neighbors in adj.items() if len(neighbors) >= min_conn}
        filtered_adj = {u: {n for n in neighbors if n in users_to_keep} for u, neighbors in adj.items() if u in users_to_keep}

        # Build nodes with metadata
        nodes = []
        for u in filtered_adj:
            meta = metadata.get(u, {})
            node = {
                'id': u,
                'display_name': meta.get('name', u),
                'group': meta.get('group', 'default'),
                'activity_level': meta.get('activity_level', 0),
                'connection_count': len(filtered_adj[u])
            }
            nodes.append(node)

        # Build edges
        edges = []
        seen = set()
        for u, neighbors in filtered_adj.items():
            for v in neighbors:
                if (u, v) not in seen and (v, u) not in seen:
                    edges.append({'source': u, 'target': v, 'weight': 1.0})
                    seen.add((u, v))

        # Calculate centrality
        if centrality == 'degree':
            for node in nodes:
                nid = node['id']
                total_nodes = len(nodes)
                node['centrality'] = (node['connection_count'] / (total_nodes - 1)) if total_nodes > 1 else 0.0
        elif centrality == 'betweenness':
            # Simplified betweenness: count shortest paths through node
            # Use BFS from each node
            betweenness = defaultdict(float)
            all_nodes = list(filtered_adj.keys())
            for s in all_nodes:
                # BFS to find shortest paths
                queue = [s]
                dist = {s: 0}
                paths = {s: [[s]]}
                while queue:
                    current = queue.pop(0)
                    for neighbor in filtered_adj[current]:
                        if neighbor not in dist:
                            dist[neighbor] = dist[current] + 1
                            queue.append(neighbor)
                            paths[neighbor] = [path + [neighbor] for path in paths[current]]
                        elif dist[neighbor] == dist[current] + 1:
                            paths[neighbor].extend([path + [neighbor] for path in paths[current]])
                # Count betweenness contributions
                for t in all_nodes:
                    if t == s:
                        continue
                    if t in paths:
                        total_paths = len(paths[t])
                        if total_paths > 0:
                            for path in paths[t]:
                                for node_in_path in path[1:-1]:
                                    betweenness[node_in_path] += 1.0 / total_paths
            # Normalize
            max_b = max(betweenness.values()) if betweenness else 1
            for node in nodes:
                node['centrality'] = betweenness.get(node['id'], 0) / max_b if max_b > 0 else 0.0
        elif centrality == 'closeness':
            # Closeness centrality: 1 / (sum of distances to all other nodes)
            closeness = {}
            for s in all_nodes:
                queue = [s]
                dist = {s: 0}
                while queue:
                    current = queue.pop(0)
                    for neighbor in filtered_adj[current]:
                        if neighbor not in dist:
                            dist[neighbor] = dist[current] + 1
                            queue.append(neighbor)
                total_dist = sum(dist.values())
                if total_dist > 0 and len(dist) > 1:
                    closeness[s] = (len(dist) - 1) / total_dist
                else:
                    closeness[s] = 0.0
            max_c = max(closeness.values()) if closeness else 1
            for node in nodes:
                node['centrality'] = closeness.get(node['id'], 0) / max_c if max_c > 0 else 0.0

        result = {
            'graph': {
                'nodes': nodes,
                'edges': edges
            },
            'summary': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'density': (2 * len(edges)) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0.0
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "generate_social_network_graph",
    "description": "Generate a social network visualization showing relationships and connections between users based on their interaction data, returning a structured graph representation (nodes and edges) for dashboard display.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "user_connections": {
            "type": "array",
            "description": "Array of connection pairs representing relationships between users. Each pair is [user_id_A, user_id_B].",
            "items": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {
                    "type": "string"
                }
            }
        },
        "user_metadata": {
            "type": "object",
            "description": "Optional: Object mapping user_id to metadata such as display name, group, or activity level. Example format: {\"user1\": {\"name\": \"Alice\", \"group\": \"engineering\"}}.",
            "default": {}
        },
        "min_connections": {
            "type": "integer",
            "description": "Optional: Minimum number of connections a user must have to be included in the graph. Default is 1.",
            "default": 1
        },
        "centrality_metric": {
            "type": "string",
            "description": "Optional: Algorithm to calculate node importance. Options: 'degree', 'betweenness', 'closeness'.",
            "enum": [
                "degree",
                "betweenness",
                "closeness"
            ],
            "default": "degree"
        }
    },
    "required": [
        "user_connections"
    ]
},
}
