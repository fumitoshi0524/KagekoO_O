"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        athlete_name = data.get("athlete_name")
        metrics = data.get("metrics")
        if not athlete_name or not metrics:
            return json.dumps({"error": "Missing required fields: athlete_name and metrics"})
        if len(metrics) < 3:
            return json.dumps({"error": "At least three metrics are required for a radar chart"})
        max_possible = data.get("max_possible_score", 100)
        if max_possible <= 0:
            return json.dumps({"error": "max_possible_score must be positive"})
        
        normalized = {}
        for metric, score in metrics.items():
            if not isinstance(score, (int, float)):
                return json.dumps({"error": f"Metric '{metric}' has non-numeric value"})
            normalized[metric] = round((score / max_possible) * 100, 2)
        
        result = {
            "chart_type": "radar",
            "athlete_name": athlete_name,
            "sport": data.get("sport", ""),
            "date": data.get("date", ""),
            "metrics": list(normalized.keys()),
            "score_values": normalized,
            "display_unit": "percentage (0-100)",
            "data_for_visualization": {
                "labels": list(normalized.keys()),
                "datasets": [
                    {
                        "label": athlete_name,
                        "data": [normalized[m] for m in normalized.keys()],
                        "fill": True
                    }
                ]
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})



TOOL_SPEC = {
    "name": "sports_performance_radar_chart",
    "description": "Generate a radar chart data structure for visualizing an athlete's performance across multiple metrics such as speed, strength, agility, endurance, and technique. Returns a JSON payload containing the chart configuration and normalized scores for radar plotting.",
    "category": "visualization",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "athlete_name": {
            "type": "string",
            "description": "Name of the athlete for labeling the radar chart"
        },
        "metrics": {
            "type": "object",
            "description": "Object where keys are metric names (e.g., speed, strength) and values are raw scores (numeric). Metrics must be at least three for a meaningful radar chart.",
            "patternProperties": {
                "^[a-zA-Z]+$": {
                    "type": "number"
                }
            },
            "minProperties": 3
        },
        "max_possible_score": {
            "type": "number",
            "description": "Optional: The maximum possible raw score for each metric (default 100). All scores will be normalized to 0-100 based on this value.",
            "default": 100
        },
        "sport": {
            "type": "string",
            "description": "Optional: The sport context (e.g., soccer, basketball) for additional labeling, if provided"
        },
        "date": {
            "type": "string",
            "format": "date",
            "description": "Optional: Date of assessment (YYYY-MM-DD format) for time-series tracking"
        }
    },
    "required": [
        "athlete_name",
        "metrics"
    ]
},
}
