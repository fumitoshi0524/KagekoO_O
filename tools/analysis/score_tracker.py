"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Track scores for a game or match, compute statistics."""
    try:
        data = json.loads(payload)
        mode = str(data.get("mode", "score")).lower().strip()
    except (json.JSONDecodeError, TypeError):
        return "error: invalid payload"

    if mode == "score":
        team_a = str(data.get("team_a", "Team A"))
        team_b = str(data.get("team_b", "Team B"))
        score_a = int(data.get("score_a", 0))
        score_b = int(data.get("score_b", 0))
        winner = team_a if score_a > score_b else team_b if score_b > score_a else "Draw"
        return json.dumps({
            "match": f"{team_a} vs {team_b}",
            "score": {team_a: score_a, team_b: score_b},
            "winner": winner,
            "total_points": score_a + score_b,
        }, indent=2, ensure_ascii=False)

    elif mode == "stats":
        scores_input = data.get("scores", [])
        if not isinstance(scores_input, list) or len(scores_input) == 0:
            return "error: 'scores' must be a non-empty list of numbers"
        scores = [float(s) for s in scores_input]
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        return json.dumps({
            "count": len(scores),
            "total": sum(scores),
            "average": round(avg, 2),
            "min": min(scores),
            "max": max(scores),
            "std_dev": round(variance ** 0.5, 2),
            "range": max(scores) - min(scores),
        }, indent=2)

    elif mode == "standings":
        teams = data.get("teams", [])
        if not isinstance(teams, list):
            return "error: 'teams' must be a list of {name, wins, losses, draws}"
        standings = []
        for t in teams:
            if not isinstance(t, dict):
                continue
            name = str(t.get("name", "Unknown"))
            wins = int(t.get("wins", 0))
            losses = int(t.get("losses", 0))
            draws = int(t.get("draws", 0))
            points = wins * 3 + draws
            played = wins + losses + draws
            win_pct = round(wins / played, 3) if played > 0 else 0.0
            standings.append({
                "name": name, "played": played, "wins": wins,
                "losses": losses, "draws": draws, "points": points,
                "win_pct": win_pct,
            })
        standings.sort(key=lambda x: (-x["points"], -x["win_pct"]))
        return json.dumps({"standings": standings}, indent=2, ensure_ascii=False)

    return f"error: unknown mode '{mode}'. Use: score, stats, standings"


TOOL_SPEC = {
    "name": "score_tracker",
    "description": "Track sports or game scores, compute game/match statistics (average, std_dev, range), and calculate league standings from win/loss/draw records.",
    "category": "analysis",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "description": "Operation: 'score' for a single match result, 'stats' for numeric statistics, 'standings' for league table.",
                "enum": ["score", "stats", "standings"]
            },
            "team_a": {"type": "string", "description": "First team name (for score mode)."},
            "team_b": {"type": "string", "description": "Second team name (for score mode)."},
            "score_a": {"type": "integer", "description": "First team score (for score mode)."},
            "score_b": {"type": "integer", "description": "Second team score (for score mode)."},
            "scores": {"type": "array", "description": "List of numeric scores to analyze (for stats mode)."},
            "teams": {"type": "array", "description": "List of {name, wins, losses, draws} objects (for standings mode)."}
        },
        "required": ["mode"]
    }
}
