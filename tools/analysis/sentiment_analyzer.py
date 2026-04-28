"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze sentiment of social texts."""
    import json
    import math

    try:
        data = json.loads(payload)
        texts = data.get("texts")
        if not texts or not isinstance(texts, list):
            return json.dumps({"error": "Missing or invalid 'texts' parameter, must be a non-empty list."})
        if len(texts) > 100:
            return json.dumps({"error": "Maximum 100 texts allowed."})

        # Simple keyword-based sentiment analysis for demonstration
        positive_words = ["love", "great", "happy", "amazing", "excellent", "wonderful", "fantastic", "joy", "fun", "best"]
        negative_words = ["hate", "terrible", "awful", "sad", "angry", "worst", "horrible", "bad", "ugly", "disappointed"]
        emotions = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}

        results = []
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                results.append({"text": text, "error": "Invalid or empty text"})
                continue

            lower_text = text.lower()
            words = lower_text.split()
            pos_count = sum(1 for w in words if w in positive_words)
            neg_count = sum(1 for w in words if w in negative_words)
            total = pos_count + neg_count

            if total == 0:
                sentiment = "neutral"
                confidence = 0.5
                dominant_emotion = "neutral"
            else:
                ratio = pos_count / total
                if ratio > 0.6:
                    sentiment = "positive"
                    confidence = min(0.5 + ratio * 0.4, 0.95)
                    dominant_emotion = "joy" if ratio > 0.8 else "happiness"
                elif ratio < 0.4:
                    sentiment = "negative"
                    confidence = min(0.5 + (1 - ratio) * 0.4, 0.95)
                    dominant_emotion = "anger" if ratio < 0.2 else "sadness"
                else:
                    sentiment = "neutral"
                    confidence = 0.5
                    dominant_emotion = "neutral"

            results.append({
                "text": text,
                "sentiment": sentiment,
                "confidence": round(confidence, 2),
                "dominant_emotion": dominant_emotion
            })

        return json.dumps({"results": results}, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {e}"})
    except Exception as e:
        return json.dumps({"error": str(e)})



TOOL_SPEC = {
    "name": "sentiment_analyzer",
    "description": "Analyze the sentiment of social media posts or comments, detecting positive, negative, or neutral emotional tone, and return a confidence score and dominant emotion for each text input.",
    "category": "analysis",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "texts": {
            "type": "array",
            "description": "List of text strings from social platforms (e.g., tweets, comments) to analyze sentiment for.",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 280
            },
            "minItems": 1,
            "maxItems": 100
        }
    },
    "required": [
        "texts"
    ]
},
}
