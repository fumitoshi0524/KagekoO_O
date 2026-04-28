"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Convert an amount between two currencies using provided exchange rate or lookup."""
    try:
        data = json.loads(payload)
        amount = float(data.get("amount", 0))
        from_currency = str(data.get("from", "USD")).upper().strip()
        to_currency = str(data.get("to", "CNY")).upper().strip()
        rate = data.get("rate")
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return f"error: invalid input — {e}"

    if amount <= 0:
        return "error: amount must be positive"

    # Common exchange rate reference (approximate, user should provide rate for accuracy)
    _reference_rates = {
        "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5,
        "CNY": 7.24, "KRW": 1350.0, "INR": 83.5, "CAD": 1.37,
        "AUD": 1.53, "CHF": 0.88, "HKD": 7.82, "SGD": 1.34,
    }

    if rate is not None:
        rate_value = float(rate)
    elif from_currency in _reference_rates and to_currency in _reference_rates:
        rate_value = _reference_rates[to_currency] / _reference_rates[from_currency]
    else:
        return json.dumps({
            "error": "Exchange rate not available. Provide a 'rate' value.",
            "amount": amount,
            "from": from_currency,
            "to": to_currency,
        }, indent=2)

    converted = round(amount * rate_value, 4)
    return json.dumps({
        "amount": amount,
        "from": from_currency,
        "to": to_currency,
        "rate": round(rate_value, 6),
        "result": converted,
    }, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "currency_convert",
    "description": "Convert an amount between two currencies using a provided exchange rate or built-in reference rates for common currencies (USD, EUR, GBP, JPY, CNY, etc.).",
    "category": "operations",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "description": "The amount to convert (must be positive)."
            },
            "from": {
                "type": "string",
                "description": "Source currency code (e.g. USD, EUR, CNY)."
            },
            "to": {
                "type": "string",
                "description": "Target currency code (e.g. USD, EUR, CNY)."
            },
            "rate": {
                "type": "number",
                "description": "Optional: custom exchange rate (from -> to). If omitted, uses built-in reference rates."
            }
        },
        "required": ["amount", "from", "to"]
    }
}
