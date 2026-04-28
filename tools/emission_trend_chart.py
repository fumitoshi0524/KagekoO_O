"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json

    try:
        data = json.loads(payload)
        country_code = data.get("country_code")
        sector = data.get("sector", "total")
        start_year = data.get("start_year")
        end_year = data.get("end_year")
        chart_type = data.get("chart_type", "line")

        if not all([country_code, start_year, end_year]):
            return json.dumps({"error": "Missing required fields: country_code, start_year, end_year"})

        if not isinstance(start_year, int) or not isinstance(end_year, int):
            return json.dumps({"error": "start_year and end_year must be integers"})

        if start_year < 1990 or end_year > 2025 or start_year > end_year:
            return json.dumps({"error": "Invalid year range: must be 1990-2025 and start_year <= end_year"})

        # Simulated emission data in Mt CO2-equivalent
        import random
        random.seed(hash(f"{country_code}-{sector}") % (2**31))
        years = list(range(start_year, end_year + 1))
        base_emission = random.uniform(100, 5000)
        trend_data = []
        for year in years:
            noise = random.uniform(-20, 20)
            annual_change = -random.uniform(0, 10) if random.random() < 0.6 else random.uniform(0, 8)
            base_emission += annual_change + noise
            trend_data.append({
                "year": year,
                "emissions_mt_co2e": round(max(base_emission + (year - years[0]) * 0.3, 0), 2)
            })

        result = {
            "country_code": country_code,
            "sector": sector,
            "chart_type": chart_type,
            "title": f"{sector.capitalize()} sector GHG emissions for {country_code} ({start_year}-{end_year})",
            "unit": "Mt CO₂-equivalent",
            "data": trend_data,
            "summary": {
                "total_emissions_last_year": trend_data[-1]["emissions_mt_co2e"],
                "change_from_start_pct": round((trend_data[-1]["emissions_mt_co2e"] - trend_data[0]["emissions_mt_co2e"]) / trend_data[0]["emissions_mt_co2e"] * 100, 2)
            }
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


TOOL_SPEC = {
    "name": "emission_trend_chart",
    "description": "Generate a multi-year trend visualization of greenhouse gas emissions by country and sector, returning chart configuration data for dashboard embedding or report generation.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "country_code": {
            "type": "string",
            "description": "ISO 3166-1 alpha-2 country code (e.g., 'US', 'CN', 'DE') for the country to visualize.",
            "examples": [
                "US",
                "CN",
                "DE"
            ]
        },
        "sector": {
            "type": "string",
            "description": "Optional: Emissions sector to filter. Defaults to 'total' if omitted.",
            "enum": [
                "total",
                "energy",
                "industry",
                "agriculture",
                "waste",
                "land_use"
            ],
            "examples": [
                "energy"
            ]
        },
        "start_year": {
            "type": "integer",
            "description": "Start year for the trend data (inclusive, between 1990 and current year).",
            "minimum": 1990,
            "maximum": 2025,
            "examples": [
                2015
            ]
        },
        "end_year": {
            "type": "integer",
            "description": "End year for the trend data (inclusive, between 1990 and current year, must be >= start_year).",
            "minimum": 1990,
            "maximum": 2025,
            "examples": [
                2023
            ]
        },
        "chart_type": {
            "type": "string",
            "description": "Optional: Type of chart to generate. Defaults to 'line'.",
            "enum": [
                "line",
                "bar",
                "area"
            ],
            "examples": [
                "line"
            ]
        }
    },
    "required": [
        "country_code",
        "start_year",
        "end_year"
    ]
},
}
