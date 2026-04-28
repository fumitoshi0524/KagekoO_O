"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        culture_a = data.get('culture_a')
        culture_b = data.get('culture_b')
        if not culture_a or not culture_b:
            return json.dumps({"error": "Both culture_a and culture_b are required."})
        aspects = data.get('aspects', ['language', 'religion', 'cuisine', 'art', 'history', 'festivals', 'philosophy', 'music'])
        # Simulated knowledge base: mapping of cultures to aspect scores (0-1)
        culture_db = {
            "Japanese": {"language": 0.2, "religion": 0.4, "cuisine": 0.9, "art": 0.8, "history": 0.7, "festivals": 0.6, "philosophy": 0.3, "music": 0.5},
            "Chinese": {"language": 0.9, "religion": 0.5, "cuisine": 0.8, "art": 0.7, "history": 0.9, "festivals": 0.8, "philosophy": 0.9, "music": 0.6},
            "Italian": {"language": 0.8, "religion": 0.9, "cuisine": 0.9, "art": 0.9, "history": 0.8, "festivals": 0.7, "philosophy": 0.2, "music": 0.7},
            "French": {"language": 0.8, "religion": 0.7, "cuisine": 0.9, "art": 0.9, "history": 0.8, "festivals": 0.6, "philosophy": 0.4, "music": 0.6},
            "Indian": {"language": 0.3, "religion": 0.8, "cuisine": 0.7, "art": 0.6, "history": 0.8, "festivals": 0.9, "philosophy": 0.9, "music": 0.9},
            "Egyptian": {"language": 0.4, "religion": 0.6, "cuisine": 0.5, "art": 0.9, "history": 0.9, "festivals": 0.4, "philosophy": 0.5, "music": 0.3},
            "Brazilian": {"language": 0.5, "religion": 0.8, "cuisine": 0.7, "art": 0.5, "history": 0.6, "festivals": 0.9, "philosophy": 0.1, "music": 0.9}
        }
        if culture_a not in culture_db or culture_b not in culture_db:
            missing = [c for c in [culture_a, culture_b] if c not in culture_db]
            return json.dumps({"error": f"Cultures not found: {missing}"})
        scores_a = culture_db[culture_a]
        scores_b = culture_db[culture_b]
        selected_aspects = [a for a in aspects if a in scores_a and a in scores_b]
        if not selected_aspects:
            return json.dumps({"error": "No valid aspects provided."})
        similarities = []
        for aspect in selected_aspects:
            diff = abs(scores_a[aspect] - scores_b[aspect])
            sim = 1.0 - diff
            similarities.append({"aspect": aspect, "score": round(sim, 2)})
        overall_sim = round(sum(s["score"] for s in similarities) / len(similarities), 2)
        result = {
            "culture_a": culture_a,
            "culture_b": culture_b,
            "overall_similarity": overall_sim,
            "aspects_compared": selected_aspects,
            "similarity_by_aspect": similarities
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})



TOOL_SPEC = {
    "name": "cultural_similarity",
    "description": "Compute a similarity score between two cultures based on their shared traditions, languages, and historical influences. Returns a normalized similarity index and a list of overlapping cultural elements.",
    "category": "analysis",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "culture_a": {
            "type": "string",
            "description": "Name of the first culture (e.g., 'Japanese', 'Italian'). Must be a recognized cultural identifier."
        },
        "culture_b": {
            "type": "string",
            "description": "Name of the second culture (e.g., 'Chinese', 'French'). Must be a recognized cultural identifier."
        },
        "aspects": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "language",
                    "religion",
                    "cuisine",
                    "art",
                    "history",
                    "festivals",
                    "philosophy",
                    "music"
                ]
            },
            "description": "Optional: List of cultural aspects to consider for similarity. If omitted, all aspects are used."
        }
    },
    "required": [
        "culture_a",
        "culture_b"
    ]
},
}
