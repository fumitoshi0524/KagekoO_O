"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Evaluate an athlete's readiness for training by combining subjective wellness metrics with optional resting heart rate."""
    import json
    try:
        data = json.loads(payload)
        required = ['athlete_id', 'sleep_quality', 'fatigue_level', 'mood_score', 'muscle_soreness']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required field: {field}'}, ensure_ascii=False)
        # Validate integer ranges
        for field in ['sleep_quality', 'fatigue_level', 'mood_score', 'muscle_soreness']:
            val = data[field]
            if not isinstance(val, int) or val < 1 or val > 5:
                return json.dumps({'error': f'{field} must be integer between 1 and 5'}, ensure_ascii=False)
        # Calculate wellness score (average of 4 metrics, scaled to 0-100)
        wellness = (data['sleep_quality'] + data['fatigue_level'] + data['mood_score'] + data['muscle_soreness']) / 4.0
        wellness_score = round((wellness - 1) / 4 * 100, 1)  # 0 = worst, 100 = best
        # Adjust for resting heart rate if provided
        hr_adjustment = 0
        if 'resting_heart_rate' in data and data['resting_heart_rate'] is not None:
            hr = data['resting_heart_rate']
            # Assume baseline 60 bpm
            if hr < 50:
                hr_adjustment = 5  # excellent recovery
            elif hr < 60:
                hr_adjustment = 2  # good
            elif hr <= 70:
                hr_adjustment = 0
            elif hr <= 80:
                hr_adjustment = -3  # poor recovery
            else:
                hr_adjustment = -8  # very poor recovery
        readiness_score = min(100, max(0, wellness_score + hr_adjustment))
        # Generate recommendation
        if readiness_score >= 80:
            recommendation = 'Excellent readiness. Athlete can engage in high-intensity training or competition.'
        elif readiness_score >= 60:
            recommendation = 'Good readiness. Recommend moderate training with optional intensity increase.'
        elif readiness_score >= 40:
            recommendation = 'Fair readiness. Suggest light training or active recovery session.'
        else:
            recommendation = 'Poor readiness. Recommend rest day or low-impact recovery activities.'
        result = {
            'athlete_id': data['athlete_id'],
            'readiness_score': readiness_score,
            'recommendation': recommendation
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'An unexpected error occurred: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "athlete_health_monitor",
    "description": "Evaluate an athlete's readiness for training by combining subjective wellness metrics (sleep quality, fatigue, mood, muscle soreness) with an optional resting heart rate to produce a readiness score and actionable recommendation.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "athlete_id": {
            "type": "string",
            "description": "Unique identifier for the athlete (e.g., UUID or internal ID)."
        },
        "sleep_quality": {
            "type": "integer",
            "description": "Subjective sleep quality rating on a scale from 1 (very poor) to 5 (excellent).",
            "minimum": 1,
            "maximum": 5
        },
        "fatigue_level": {
            "type": "integer",
            "description": "Subjective fatigue level on a scale from 1 (very low energy) to 5 (fully rested).",
            "minimum": 1,
            "maximum": 5
        },
        "mood_score": {
            "type": "integer",
            "description": "Subjective mood score on a scale from 1 (irritable/depressed) to 5 (very positive).",
            "minimum": 1,
            "maximum": 5
        },
        "muscle_soreness": {
            "type": "integer",
            "description": "Subjective muscle soreness level on a scale from 1 (severe soreness) to 5 (no soreness).",
            "minimum": 1,
            "maximum": 5
        },
        "resting_heart_rate": {
            "type": "integer",
            "description": "Optional: morning resting heart rate in beats per minute (bpm). Lower values relative to baseline indicate better recovery.",
            "minimum": 30,
            "maximum": 120
        }
    },
    "required": [
        "athlete_id",
        "sleep_quality",
        "fatigue_level",
        "mood_score",
        "muscle_soreness"
    ]
},
}
