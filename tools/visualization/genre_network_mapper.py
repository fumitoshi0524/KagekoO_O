"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        source = data.get('source_genre')
        if not source:
            return json.dumps({'error': 'Missing required field: source_genre'})
        depth = data.get('depth', 2)
        if not (1 <= depth <= 5):
            return json.dumps({'error': 'depth must be between 1 and 5'})
        include_influences = data.get('include_influences', False)
        min_weight = data.get('min_weight', 0.1)
        if not (0.0 <= min_weight <= 1.0):
            return json.dumps({'error': 'min_weight must be between 0.0 and 1.0'})
        
        # Simulated genre graph database (in production, this would be a real data source)
        genre_graph = {
            "science fiction": {
                "subgenres": ["cyberpunk", "space opera", "time travel", "biopunk"],
                "influences": ["fantasy", "horror"],
                "influenced": ["superhero", "dystopian"],
                "weight": 0.85
            },
            "hip hop": {
                "subgenres": ["trap", "boom bap", "cloud rap", "drill"],
                "influences": ["funk", "soul", "reggae"],
                "influenced": ["pop", "r&b"],
                "weight": 0.92
            },
            "RPG": {
                "subgenres": ["JRPG", "action RPG", "tactical RPG", "MMORPG"],
                "influences": ["tabletop games", "fantasy literature"],
                "influenced": ["adventure games", "simulation games"],
                "weight": 0.88
            },
            "fantasy": {
                "subgenres": ["high fantasy", "urban fantasy", "dark fantasy", "sword and sorcery"],
                "influences": ["mythology", "folklore"],
                "influenced": ["science fiction", "superhero"],
                "weight": 0.78
            },
            "horror": {
                "subgenres": ["cosmic horror", "slasher", "psychological horror", "folk horror"],
                "influences": ["gothic literature"],
                "influenced": ["science fiction", "thriller"],
                "weight": 0.72
            },
            "pop": {
                "subgenres": ["synth-pop", "electropop", "K-pop", "teen pop"],
                "influences": ["rock", "hip hop"],
                "influenced": ["disco", "country pop"],
                "weight": 0.95
            },
            "trap": {
                "subgenres": ["drill", "trap soul", "Latin trap"],
                "influences": ["hip hop", "electronic"],
                "influenced": ["pop", "reggeton"],
                "weight": 0.89
            },
            "cyberpunk": {
                "subgenres": ["cyberpunk 2077 genre", "post-cyberpunk"],
                "influences": ["science fiction", "noir"],
                "influenced": ["biopunk", "dieselpunk"],
                "weight": 0.65
            }
        }
        
        # Build the network from the source
        def explore_genre(current_genre, current_depth, visited):
            if current_depth > depth or current_genre in visited:
                return []
            visited.add(current_genre)
            nodes = []
            edges = []
            info = genre_graph.get(current_genre, {})
            weight = info.get('weight', 0.5)
            if weight >= min_weight:
                nodes.append({'id': current_genre, 'group': 'explored', 'weight': weight})
                # Subgenres
                for sub in info.get('subgenres', []):
                    sub_info = genre_graph.get(sub, {})
                    sub_weight = sub_info.get('weight', 0.3)
                    if sub_weight >= min_weight:
                        nodes.append({'id': sub, 'group': 'subgenre', 'weight': sub_weight})
                        edges.append({'source': current_genre, 'target': sub, 'type': 'subgenre', 'strength': 0.7})
                        # Recursively explore subgenres
                        sub_nodes, sub_edges = explore_genre(sub, current_depth + 1, visited)
                        nodes.extend(sub_nodes)
                        edges.extend(sub_edges)
                # Influences (backward direction)
                if include_influences:
                    for infl in info.get('influences', []):
                        infl_info = genre_graph.get(infl, {})
                        infl_weight = infl_info.get('weight', 0.3)
                        if infl_weight >= min_weight:
                            nodes.append({'id': infl, 'group': 'influence', 'weight': infl_weight})
                            edges.append({'source': infl, 'target': current_genre, 'type': 'influence', 'strength': 0.5})
                # Influenced (forward direction)
                for infl in info.get('influenced', []):
                    infl_info = genre_graph.get(infl, {})
                    infl_weight = infl_info.get('weight', 0.3)
                    if infl_weight >= min_weight:
                        nodes.append({'id': infl, 'group': 'influenced', 'weight': infl_weight})
                        edges.append({'source': current_genre, 'target': infl, 'type': 'influenced', 'strength': 0.5})
            return nodes, edges
        
        visited = set()
        all_nodes, all_edges = explore_genre(source, 1, visited)
        
        # Deduplicate nodes and edges
        seen_ids = set()
        unique_nodes = []
        for node in all_nodes:
            if node['id'] not in seen_ids:
                seen_ids.add(node['id'])
                unique_nodes.append(node)
        
        edge_keys = set()
        unique_edges = []
        for edge in all_edges:
            key = (edge['source'], edge['target'], edge['type'])
            if key not in edge_keys:
                edge_keys.add(key)
                unique_edges.append(edge)
        
        result = {
            'source': source,
            'depth': depth,
            'nodes': unique_nodes,
            'edges': unique_edges,
            'metadata': {
                'total_nodes': len(unique_nodes),
                'total_edges': len(unique_edges),
                'generated_at': 'simulated_data'
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "genre_network_mapper",
    "description": "Generate an interactive network graph of entertainment genres and subgenres showing relationships, popularity weights, and cross-genre influence scores, returning a D3.js-compatible JSON structure for visualization in dashboards or reports.",
    "category": "visualization",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "source_genre": {
            "type": "string",
            "description": "The primary entertainment genre to analyze (e.g., 'science fiction', 'hip hop', 'RPG').",
            "examples": [
                "science fiction",
                "hip hop",
                "RPG"
            ]
        },
        "depth": {
            "type": "integer",
            "description": "Optional: Number of relationship levels to traverse from the source genre (min 1, max 5). Default is 2.",
            "minimum": 1,
            "maximum": 5,
            "default": 2
        },
        "include_influences": {
            "type": "boolean",
            "description": "Optional: If True, include backward influence edges (genres that influenced the network). Default is False.",
            "default": False
        },
        "min_weight": {
            "type": "number",
            "description": "Optional: Minimum popularity weight (0.0 to 1.0) for a node to be included. Default is 0.1.",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 0.1
        }
    },
    "required": [
        "source_genre"
    ]
},
}
