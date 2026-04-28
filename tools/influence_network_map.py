"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        connections = data['connections']
        influence_scores = data.get('influence_scores', {})
        community_algorithm = data.get('community_algorithm', 'louvain')
        centrality_cutoff = data.get('centrality_cutoff', 0.0)
        
        if not isinstance(connections, list) or not connections:
            return json.dumps({'error': 'connections must be a non-empty list'}, ensure_ascii=False)
        if not isinstance(influence_scores, dict):
            return json.dumps({'error': 'influence_scores must be an object'}, ensure_ascii=False)
        if community_algorithm not in ['louvain', 'girvan_newman', 'label_propagation']:
            return json.dumps({'error': 'Invalid community_algorithm'}, ensure_ascii=False)
        
        # Build graph
        nodes = {}
        edges = []
        for conn in connections:
            src = conn['source']
            tgt = conn['target']
            if src not in nodes:
                nodes[src] = {'id': src, 'influence': influence_scores.get(src, 0.5), 'communities': []}
            if tgt not in nodes:
                nodes[tgt] = {'id': tgt, 'influence': influence_scores.get(tgt, 0.5), 'communities': []}
            edges.append({'source': src, 'target': tgt})
        
        # Compute degree centrality
        degree_counts = {node: 0 for node in nodes}
        for e in edges:
            degree_counts[e['source']] += 1
            degree_counts[e['target']] += 1
        n = len(nodes)
        if n > 1:
            max_degree = max(degree_counts.values())
            for node in nodes:
                centrality = degree_counts[node] / (n - 1) if n > 1 else 0
                nodes[node]['centrality'] = round(centrality, 4)
        else:
            for node in nodes:
                nodes[node]['centrality'] = 0.0
        
        # Filter nodes by centrality cutoff
        filtered_node_ids = [nid for nid, ndata in nodes.items() if ndata['centrality'] >= centrality_cutoff]
        # Filter edges accordingly
        filtered_edges = [e for e in edges if e['source'] in filtered_node_ids and e['target'] in filtered_node_ids]
        # Recompute nodes list after filter
        filtered_nodes = [nodes[nid] for nid in filtered_node_ids]
        
        # Simple community detection (Louvain-like: greedy modularity optimization)
        # Assign each node to its own community initially
        community = {nid: i for i, nid in enumerate(filtered_node_ids)}
        # One pass of modularity optimization (simplified): merge nodes that share edges
        changed = True
        while changed:
            changed = False
            for i, nid1 in enumerate(filtered_node_ids):
                for j, nid2 in enumerate(filtered_node_ids):
                    if i >= j: continue
                    # Check if edge exists
                    edge_exists = any((e['source'] == nid1 and e['target'] == nid2) or (e['source'] == nid2 and e['target'] == nid1) for e in filtered_edges)
                    if edge_exists and community[nid1] != community[nid2]:
                        # Merge communities (assign all nodes with community of nid2 to nid1's community)
                        old_comm = community[nid2]
                        new_comm = community[nid1]
                        for nid in filtered_node_ids:
                            if community[nid] == old_comm:
                                community[nid] = new_comm
                        changed = True
                        break
                if changed:
                    break
        
        # Assign communities to nodes and find top influencers per community
        community_nodes = {}
        for nid in filtered_node_ids:
            comm_id = community[nid]
            if comm_id not in community_nodes:
                community_nodes[comm_id] = []
            community_nodes[comm_id].append(nid)
        
        # For each community, find top influencers (sorted by influence score)
        top_influencers = {}
        for comm_id, members in community_nodes.items():
            sorted_members = sorted(members, key=lambda x: nodes[x]['influence'], reverse=True)
            top_influencers[str(comm_id)] = sorted_members[:3]  # top 3
        
        # Build result
        result = {
            'nodes': [{
                'id': nd['id'],
                'influence': nd['influence'],
                'centrality': nd['centrality'],
                'community': community[nd['id']]
            } for nd in filtered_nodes],
            'edges': filtered_edges,
            'metadata': {
                'total_nodes': len(filtered_nodes),
                'total_edges': len(filtered_edges),
                'num_communities': len(community_nodes),
                'top_influencers': top_influencers
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "influence_network_map",
    "description": "Analyze social network relationships from a list of user connections and influence scores, generating a structured visualization map of key influencers, their communities, and centrality metrics. Returns JSON containing node-link data for chart rendering and community detection results.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "connections": {
            "type": "array",
            "description": "List of user connection pairs representing edges in the social graph, each object must contain 'source' and 'target' user IDs.",
            "items": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "User ID of the connection initiator."
                    },
                    "target": {
                        "type": "string",
                        "description": "User ID of the connection receiver."
                    }
                },
                "required": [
                    "source",
                    "target"
                ]
            }
        },
        "influence_scores": {
            "type": "object",
            "description": "Object mapping user IDs (strings) to their influence score (float between 0 and 1). Users not listed default to 0.5.",
            "additionalProperties": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            }
        },
        "community_algorithm": {
            "type": "string",
            "description": "Optional: Community detection algorithm to apply. Default: 'louvain'. Options: louvain, girvan_newman, label_propagation.",
            "enum": [
                "louvain",
                "girvan_newman",
                "label_propagation"
            ],
            "default": "louvain"
        },
        "centrality_cutoff": {
            "type": "number",
            "description": "Optional: Minimum degree centrality (0 to 1) to include a node in the visualization. Use to filter out peripheral users. Default: 0.0 (include all).",
            "minimum": 0,
            "maximum": 1,
            "default": 0.0
        }
    },
    "required": [
        "connections",
        "influence_scores"
    ]
},
}
