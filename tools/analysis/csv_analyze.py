"""Auto-generated tool module."""

from __future__ import annotations

import json
import csv
import io
from collections import Counter


def run(payload: str) -> str:
    """Analyze CSV data and return summary statistics."""
    try:
        data = json.loads(payload)
        csv_text = str(data.get("csv_data", ""))
    except (json.JSONDecodeError, TypeError):
        csv_text = payload

    if not csv_text.strip():
        return "error: no CSV data provided"

    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
    except Exception as e:
        return f"error: invalid CSV format — {e}"

    if not rows:
        return "error: CSV has no data rows"

    fieldnames = reader.fieldnames or []
    result = {
        "row_count": len(rows),
        "column_count": len(fieldnames),
        "columns": fieldnames,
    }

    col_stats = {}
    for col in fieldnames:
        values = [row.get(col, "") for row in rows]
        non_empty = [v for v in values if v.strip()]
        numeric_values = []
        for v in non_empty:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                pass

        stat = {"non_empty": len(non_empty), "empty": len(values) - len(non_empty)}
        if numeric_values:
            stat["min"] = min(numeric_values)
            stat["max"] = max(numeric_values)
            stat["mean"] = round(sum(numeric_values) / len(numeric_values), 4)
            stat["type"] = "numeric"
        elif non_empty:
            counter = Counter(non_empty)
            stat["unique_values"] = len(counter)
            stat["most_common"] = counter.most_common(3)
            stat["type"] = "text"
        else:
            stat["type"] = "empty"
        col_stats[col] = stat

    result["column_stats"] = col_stats
    return json.dumps(result, indent=2, ensure_ascii=False)


TOOL_SPEC = {
    "name": "csv_analyze",
    "description": "Analyze CSV data and return row/column counts, per-column statistics (min, max, mean for numeric; unique values for text).",
    "category": "analysis",
    "domain": "business",
    "risk_level": "read",
    "schema": {
        "type": "object",
        "properties": {
            "csv_data": {
                "type": "string",
                "description": "CSV text content with header row to analyze."
            }
        },
        "required": ["csv_data"]
    }
}
