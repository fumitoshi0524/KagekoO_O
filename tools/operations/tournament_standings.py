"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        required = ["tournament_id", "match_id", "home_team_id", "away_team_id", "home_score", "away_score"]
        for key in required:
            if key not in data:
                return json.dumps({"error": f"Missing required parameter: {key}"})
        if data["home_score"] < 0 or data["away_score"] < 0:
            return json.dumps({"error": "Scores cannot be negative"})
        # Compute result
        if data["home_score"] > data["away_score"]:
            result = "home_win"
        elif data["home_score"] < data["away_score"]:
            result = "away_win"
        else:
            result = "draw"
        # Simulate updating standings (in real would persist to DB)
        standings = {
            "tournament_id": data["tournament_id"],
            "match_id": data["match_id"],
            "result": result,
            "home_points": 3 if result == "home_win" else (1 if result == "draw" else 0),
            "away_points": 3 if result == "away_win" else (1 if result == "draw" else 0),
            "home_goal_diff": data["home_score"] - data["away_score"],
            "away_goal_diff": data["away_score"] - data["home_score"],
            "status": "recorded"
        }
        return json.dumps({"success": True, "standings_update": standings}, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"})
    except Exception as e:
        return json.dumps({"error": f"error: {e}"})


TOOL_SPEC = {
    "name": "tournament_standings",
    "description": "Update tournament standings by recording match results and recalculating team rankings (points, wins, losses, goal differential) for a given sports tournament.",
    "category": "operations",
    "domain": "sports",
    "risk_level": "low",
    "schema": {
    "type": "object",
    "properties": {
        "tournament_id": {
            "type": "string",
            "description": "Unique identifier of the tournament (e.g., 't_2025_soccer_league').",
            "examples": [
                "t_2025_soccer_league",
                "basketball_cup_2025"
            ]
        },
        "match_id": {
            "type": "string",
            "description": "Unique identifier of the completed match to record.",
            "examples": [
                "m_015",
                "game_32"
            ]
        },
        "home_team_id": {
            "type": "string",
            "description": "Identifier of the home team.",
            "examples": [
                "team_a",
                "squad_xyz"
            ]
        },
        "away_team_id": {
            "type": "string",
            "description": "Identifier of the away team.",
            "examples": [
                "team_b",
                "rival_team"
            ]
        },
        "home_score": {
            "type": "integer",
            "description": "Final score of the home team (non-negative integer).",
            "minimum": 0,
            "examples": [
                3,
                1,
                0
            ]
        },
        "away_score": {
            "type": "integer",
            "description": "Final score of the away team (non-negative integer).",
            "minimum": 0,
            "examples": [
                2,
                1,
                0
            ]
        }
    },
    "required": [
        "tournament_id",
        "match_id",
        "home_team_id",
        "away_team_id",
        "home_score",
        "away_score"
    ]
},
}
