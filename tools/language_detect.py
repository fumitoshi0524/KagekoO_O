"""Auto-generated tool module."""

from __future__ import annotations

import json
import re


def run(payload: str) -> str:
    """Detect the language of input text using character set analysis and common word patterns."""
    try:
        data = json.loads(payload)
        text = str(data.get("text", ""))
    except (json.JSONDecodeError, TypeError):
        text = payload

    if not text.strip():
        return "error: no text provided"

    text_sample = text[:500].lower()

    # Character set detection
    has_cyrillic = bool(re.search(r"[Ѐ-ӿ]", text_sample))
    has_arabic = bool(re.search(r"[؀-ۿ]", text_sample))
    has_devanagari = bool(re.search(r"[ऀ-ॿ]", text_sample))
    has_cjk = bool(re.search(r"[一-鿿぀-ゟ゠-ヿ]", text_sample))
    has_hangul = bool(re.search(r"[가-힯]", text_sample))
    has_thai = bool(re.search(r"[฀-๿]", text_sample))
    has_latin = bool(re.search(r"[a-zÀ-ɏ]", text_sample))

    scores: dict[str, float] = {}

    # Quick character set matches
    if has_cyrillic:
        scores["Russian"] = 0.9
    if has_arabic:
        scores["Arabic"] = 0.9
    if has_devanagari:
        scores["Hindi"] = 0.85
    if has_cjk and not has_hangul:
        scores["Chinese"] = 0.85
    if has_cjk and has_hangul:
        scores["Japanese"] = 0.7
    if has_hangul and not has_cjk:
        scores["Korean"] = 0.9
    if has_thai:
        scores["Thai"] = 0.9

    if has_latin:
        # Common word patterns for Latin-script languages
        patterns = {
            "English": [r"\bthe\b", r"\bis\b", r"\b(a|an)\b", r"\b(and|or)\b", r"\bin\b", r"\bto\b", r"\bof\b"],
            "French": [r"\b(le|la|les|des)\b", r"\b(est|sont)\b", r"\b(dans|sur|avec)\b", r"\b(pour|par)\b"],
            "Spanish": [r"\b(el|los|las)\b", r"\b(es|son|está)\b", r"\b(que|por|para)\b", r"\b(con|del)\b"],
            "German": [r"\b(der|die|das)\b", r"\b(ist|sind)\b", r"\b(und|oder|aber)\b", r"\b(mit|von|zu)\b"],
            "Italian": [r"\b(il|la|le|i)\b", r"\b(è|sono)\b", r"\b(che|per|con)\b", r"\b(di|da|in)\b"],
            "Portuguese": [r"\b(o|a|os|as)\b", r"\b(é|são|está)\b", r"\b(que|para|com)\b", r"\b(em|de|por)\b"],
            "Dutch": [r"\b(de|het|een)\b", r"\b(is|zijn)\b", r"\b(en|of|ook)\b", r"\b(van|in|op)\b"],
        }
        for lang, pats in patterns.items():
            score = sum(1 for p in pats if re.search(p, text_sample)) / len(pats)
            if score > 0.2:
                scores[lang] = score

    if not scores:
        if has_latin:
            scores["English"] = 0.5
        else:
            scores["Unknown"] = 0.3

    best = max(scores, key=lambda k: scores[k])
    return json.dumps({
        "detected_language": best,
        "confidence": round(scores[best], 2),
        "all_scores": {k: round(v, 2) for k, v in sorted(scores.items(), key=lambda x: -x[1])},
        "text_length": len(text),
        "character_sets_detected": {
            "latin": has_latin,
            "cyrillic": has_cyrillic,
            "arabic": has_arabic,
            "cjk": has_cjk,
            "hangul": has_hangul,
        },
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "language_detect",
    "description": "Detect the language of input text using character set analysis and common word pattern matching across English, French, Spanish, German, Italian, Portuguese, Dutch, Russian, Arabic, Hindi, Chinese, Japanese, Korean, and Thai.",
    "category": "analysis",
    "domain": "culture",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to analyze for language detection."
            }
        },
        "required": ["text"]
    }
}
