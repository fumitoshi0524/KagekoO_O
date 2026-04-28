"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a social network graph visualization from user connections."""
    import json
    try:
        data = json.loads(payload)
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        options = data.get("options", {})
        
        # Validate required inputs
        if not nodes or not edges:
            return json.dumps({"error": "Both 'nodes' and 'edges' are required."})
        
        # Build node lookup
        node_ids = set()
        for node in nodes:
            if "id" not in node:
                return json.dumps({"error": "Each node must have an 'id' field."})
            if not isinstance(node["id"], str):
                return json.dumps({"error": "Node 'id' must be a string."})
            if node["id"] in node_ids:
                return json.dumps({"error": f"Duplicate node id: {node['id']}"})
            node_ids.add(node["id"])
        
        # Validate edges and compute statistics
        edge_count = len(edges)
        validated_edges = []
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if not src or not tgt:
                return json.dumps({"error": "Each edge must have 'source' and 'target'."})
            if src not in node_ids or tgt not in node_ids:
                return json.dumps({"error": f"Edge references unknown node: {src} -> {tgt}"})
            validated_edges.append({"source": src, "target": tgt, "weight": edge.get("weight", 0.5)})
        
        # Compute derived statistics
        total_nodes = len(nodes)
        total_edges = len(validated_edges)
        avg_degree = (2 * total_edges) / total_nodes if total_nodes > 0 else 0
        # Count isolated nodes (no edges)
        connected_nodes = set()
        for e in validated_edges:
            connected_nodes.add(e["source"])
            connected_nodes.add(e["target"])
        isolated_count = total_nodes - len(connected_nodes)
        
        # Build result
        result = {
            "graph": {
                "nodes": nodes,
                "edges": validated_edges,
                "options": {
                    "layout": options.get("layout", "force"),
                    "enable_labels": options.get("enable_labels", True),
                    "edge_curved": options.get("edge_curved", False)
                }
            },
            "statistics": {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "average_degree": round(avg_degree, 2),
                "isolated_nodes": isolated_count
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})



TOOL_SPEC = {
    "name": "social_network_graph",
    "description": "Generate an interactive social network graph visualization from a list of user connections, showing nodes (users) and edges (relationships) with optional attributes such as group, influence score, and connection strength, returning a JSON representation suitable for rendering.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "description": "List of user nodes. Each node must have a unique 'id' and optionally 'group' (integer for coloring), 'influence' (float 0-1), and 'name' (display label).",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique user identifier.",
                        "examples": [
                            "user_123",
                            "alice"
                        ]
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional: Display name for the node.",
                        "examples": [
                            "Alice Johnson",
                            "Bob Smith"
                        ]
                    },
                    "group": {
                        "type": "integer",
                        "description": "Optional: Group/category for coloring (e.g., department, team).",
                        "examples": [
                            1,
                            2,
                            3
                        ]
                    },
                    "influence": {
                        "type": "number",
                        "description": "Optional: Influence score between 0 and 1, used for node sizing.",
                        "minimum": 0,
                        "maximum": 1,
                        "examples": [
                            0.75,
                            0.3
                        ]
                    }
                },
                "required": [
                    "id"
                ]
            }
        },
        "edges": {
            "type": "array",
            "description": "List of connections between users. Each edge requires 'source' and 'target' matching node ids, and optionally 'weight' (float) for connection strength.",
            "items": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source node id.",
                        "examples": [
                            "user_123",
                            "alice"
                        ]
                    },
                    "target": {
                        "type": "string",
                        "description": "Target node id.",
                        "examples": [
                            "user_456",
                            "bob"
                        ]
                    },
                    "weight": {
                        "type": "number",
                        "description": "Optional: Connection strength (e.g., number of interactions, 0-1).",
                        "minimum": 0,
                        "maximum": 1,
                        "examples": [
                            0.8,
                            0.2
                        ]
                    }
                },
                "required": [
                    "source",
                    "target"
                ]
            }
        },
        "options": {
            "type": "object",
            "description": "Optional: Additional visualization parameters.",
            "properties": {
                "layout": {
                    "type": "string",
                    "enum": [
                        "force",
                        "circular",
                        "hierarchical"
                    ],
                    "description": "Optional: Graph layout algorithm. Default is 'force'.",
                    "examples": [
                        "force"
                    ]
                },
                "enable_labels": {
                    "type": "boolean",
                    "description": "Optional: Whether to show node labels. Default true.",
                    "examples": [
                        true
                    ]
                },
                "edge_curved": {
                    "type": "boolean",
                    "description": "Optional: Use curved edges to avoid overlap. Default false.",
                    "examples": [
                        false
                    ]
                }
            }
        }
    },
    "required": [
        "nodes",
        "edges"
    ]
},
}
