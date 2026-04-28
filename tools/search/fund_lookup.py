"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        # Simulate a comprehensive mutual fund database for search
        fund_database = [
            {"id": "F001", "name": "Vanguard Total Stock Market Index", "family": "Vanguard", "category": "large_cap_equity", "inception_date": "1992-04-27", "expense_ratio": 0.03, "rating": 4, "one_year_return": 12.5, "three_year_return": 10.2, "five_year_return": 11.8},
            {"id": "F002", "name": "Fidelity Contrafund", "family": "Fidelity", "category": "large_cap_equity", "inception_date": "1967-05-17", "expense_ratio": 0.39, "rating": 5, "one_year_return": 15.3, "three_year_return": 13.1, "five_year_return": 14.2},
            {"id": "F003", "name": "PIMCO Total Return Fund", "family": "PIMCO", "category": "bond", "inception_date": "1987-05-11", "expense_ratio": 0.75, "rating": 3, "one_year_return": 3.2, "three_year_return": 2.1, "five_year_return": 2.8},
            {"id": "F004", "name": "T. Rowe Price Blue Chip Growth", "family": "T. Rowe Price", "category": "large_cap_equity", "inception_date": "1993-06-30", "expense_ratio": 0.69, "rating": 4, "one_year_return": 18.7, "three_year_return": 14.9, "five_year_return": 16.1},
            {"id": "F005", "name": "Vanguard Total Bond Market Index", "family": "Vanguard", "category": "bond", "inception_date": "1986-12-11", "expense_ratio": 0.05, "rating": 4, "one_year_return": 1.8, "three_year_return": 0.9, "five_year_return": 1.5},
            {"id": "F006", "name": "American Funds Growth Fund of America", "family": "American Funds", "category": "large_cap_equity", "inception_date": "1973-12-01", "expense_ratio": 0.63, "rating": 4, "one_year_return": 14.2, "three_year_return": 11.8, "five_year_return": 12.5},
            {"id": "F007", "name": "BlackRock Global Allocation Fund", "family": "BlackRock", "category": "balanced", "inception_date": "1989-03-01", "expense_ratio": 1.00, "rating": 3, "one_year_return": 6.5, "three_year_return": 5.2, "five_year_return": 5.9},
            {"id": "F008", "name": "Vanguard FTSE All-World ex-US Index", "family": "Vanguard", "category": "international_equity", "inception_date": "2011-01-27", "expense_ratio": 0.08, "rating": 4, "one_year_return": 9.8, "three_year_return": 7.5, "five_year_return": 8.1}
        ]
        
        results = []
        for fund in fund_database:
            # Apply fund name filter (case-insensitive substring match)
            if "fund_name" in data and data["fund_name"]:
                query = data["fund_name"].lower()
                if query not in fund["name"].lower():
                    continue
            
            # Apply fund family filter (case-insensitive exact match)
            if "fund_family" in data and data["fund_family"]:
                if data["fund_family"].lower() != fund["family"].lower():
                    continue
            
            # Apply category filter
            if "category" in data and data["category"]:
                if data["category"] != fund["category"]:
                    continue
            
            # Apply rating filter
            if "min_rating" in data and data["min_rating"] is not None:
                if fund["rating"] < data["min_rating"]:
                    continue
            
            # Apply expense ratio filter
            if "max_expense_ratio" in data and data["max_expense_ratio"] is not None:
                if fund["expense_ratio"] > data["max_expense_ratio"]:
                    continue
            
            # Apply return filter
            if "min_one_year_return" in data and data["min_one_year_return"] is not None:
                if fund["one_year_return"] < data["min_one_year_return"]:
                    continue
            
            results.append(fund)
        
        if not results:
            return json.dumps({"status": "success", "count": 0, "funds": []})
        
        return json.dumps({"status": "success", "count": len(results), "funds": results})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})



TOOL_SPEC = {
    "name": "fund_lookup",
    "description": "Search and filter mutual funds by name, fund family, category, or performance metrics and return matching fund identifiers, inception dates, expense ratios, and historical returns.",
    "category": "search",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "fund_name": {
            "type": "string",
            "description": "Partial or full mutual fund name to search for (case-insensitive, supports substring matching)"
        },
        "fund_family": {
            "type": "string",
            "description": "Name of the asset management company or fund family (e.g., Vanguard, Fidelity, BlackRock)"
        },
        "category": {
            "type": "string",
            "description": "Fund category filter based on investment style or asset class",
            "enum": [
                "large_cap_equity",
                "small_cap_equity",
                "bond",
                "balanced",
                "international_equity",
                "sector_specific",
                "money_market",
                "real_estate",
                "commodity",
                "target_date"
            ]
        },
        "min_rating": {
            "type": "integer",
            "description": "Optional: Minimum Morningstar-style star rating (1 to 5) to filter fund quality",
            "minimum": 1,
            "maximum": 5
        },
        "max_expense_ratio": {
            "type": "number",
            "description": "Optional: Maximum expense ratio percentage (e.g., 0.75 means 0.75%) to filter low-cost funds",
            "minimum": 0,
            "maximum": 5
        },
        "min_one_year_return": {
            "type": "number",
            "description": "Optional: Minimum 1-year annualized return percentage to filter funds by recent performance",
            "minimum": -100,
            "maximum": 200
        }
    },
    "required": []
},
}
