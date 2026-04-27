"""Auto-generated tool module."""

from __future__ import annotations

import json
import re
from collections import Counter


def run(payload: str) -> str:
    """Summarize text with word/sentence counts, top words, and reading time."""
    try:
        data = json.loads(payload)
        text = str(data.get("text", ""))
    except (json.JSONDecodeError, TypeError):
        text = payload

    if not text.strip():
        return "error: no text provided"

    words = re.findall(r"\b\w+\b", text.lower())
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    char_count = len(text)
    char_no_spaces = len(text.replace(" ", "").replace("\n", ""))
    word_count = len(words)
    sentence_count = len(sentences)
    paragraph_count = len(paragraphs)

    word_freq = Counter(words)
    top_words = word_freq.most_common(10)

    avg_words_per_sentence = round(word_count / sentence_count, 1) if sentence_count else 0
    reading_time_minutes = round(word_count / 200, 1)
    unique_word_ratio = round(len(word_freq) / word_count, 2) if word_count else 0

    return json.dumps({
        "char_count": char_count,
        "char_no_spaces": char_no_spaces,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "avg_words_per_sentence": avg_words_per_sentence,
        "reading_time_minutes": reading_time_minutes,
        "unique_word_ratio": unique_word_ratio,
        "top_words": [{"word": w, "count": c} for w, c in top_words],
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "text_summarize",
    "description": "Analyze and summarize text with word/sentence/paragraph counts, top keywords, reading time estimate, and unique word ratio.",
    "category": "analysis",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text content to analyze and summarize."
            }
        },
        "required": ["text"]
    }
}
