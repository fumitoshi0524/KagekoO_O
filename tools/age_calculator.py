"""Auto-generated tool module."""

from __future__ import annotations

import json
from datetime import datetime


def run(payload: str) -> str:
    """Age calculator with zodiac sign and generation info."""
    try:
        data = json.loads(payload)
        birth_date = str(data.get("birth_date", ""))
        reference_date = str(data.get("reference_date", ""))
    except (json.JSONDecodeError, TypeError):
        return "error: invalid payload — provide JSON with 'birth_date' (YYYY-MM-DD)"

    if not birth_date:
        return "error: 'birth_date' is required (YYYY-MM-DD format)"

    try:
        birth = datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        return "error: invalid date format. Use YYYY-MM-DD (e.g. 1990-05-15)"

    if reference_date:
        try:
            ref = datetime.strptime(reference_date, "%Y-%m-%d")
        except ValueError:
            return "error: invalid reference_date format. Use YYYY-MM-DD"
    else:
        ref = datetime.now()

    if birth > ref:
        return "error: birth date is after reference date"

    years = ref.year - birth.year
    if (ref.month, ref.day) < (birth.month, birth.day):
        years -= 1

    # Calculate months and days
    if ref.month >= birth.month:
        months = ref.month - birth.month
    else:
        months = 12 + ref.month - birth.month
        years_adjusted = years - 1
    if ref.day < birth.day:
        months -= 1
        if months < 0:
            months += 12

    total_days = (ref - birth).days

    zodiac = _get_zodiac(birth.month, birth.day)
    generation = _get_generation(birth.year)

    return json.dumps({
        "birth_date": birth.strftime("%Y-%m-%d"),
        "reference_date": ref.strftime("%Y-%m-%d"),
        "age_years": years,
        "age_months_remainder": max(0, months),
        "total_days": total_days,
        "zodiac_sign": zodiac,
        "generation": generation,
    }, indent=2, ensure_ascii=False)


def _get_zodiac(month: int, day: int) -> str:
    zodiac_dates = [
        (1, 20, "Capricorn"), (2, 19, "Aquarius"), (3, 21, "Pisces"),
        (4, 20, "Aries"), (5, 21, "Taurus"), (6, 21, "Gemini"),
        (7, 23, "Cancer"), (8, 23, "Leo"), (9, 23, "Virgo"),
        (10, 23, "Libra"), (11, 22, "Scorpio"), (12, 22, "Sagittarius"),
        (12, 31, "Capricorn"),
    ]
    for m, d, sign in zodiac_dates:
        if (month == m and day <= d) or (month < m):
            return sign
    return "Capricorn"


def _get_generation(year: int) -> str:
    if year >= 2013:
        return "Gen Alpha"
    if year >= 1997:
        return "Gen Z"
    if year >= 1981:
        return "Millennial"
    if year >= 1965:
        return "Gen X"
    if year >= 1946:
        return "Baby Boomer"
    return "Silent Generation"


TOOL_SPEC = {
    "name": "age_calculator",
    "description": "Calculate exact age in years from a birth date, including zodiac sign and generational cohort classification (Gen Z, Millennial, etc.).",
    "category": "analysis",
    "domain": "social",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "birth_date": {
                "type": "string",
                "description": "Birth date in YYYY-MM-DD format (e.g. 1990-05-15)."
            },
            "reference_date": {
                "type": "string",
                "description": "Optional: reference date in YYYY-MM-DD format. Defaults to today."
            }
        },
        "required": ["birth_date"]
    }
}
