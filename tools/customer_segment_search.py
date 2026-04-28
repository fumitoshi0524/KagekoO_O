"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        age = data.get('age_range', 'all')
        gender = data.get('gender', 'all')
        region = data.get('region', 'all')
        income = data.get('income_level', 'all')
        interests = data.get('interests', [])
        min_size = data.get('min_segment_size', 0)
        
        # Simulated database of segments
        segments_db = [
            {"name": "Young Urban Professionals", "description": "Tech-savvy millennials in cities with high disposable income", "size": 120000, "revenue_potential": 45000000.0, "age": "26-35", "gender": "all", "region": "north_america", "income": "high", "tags": ["technology", "career", "travel"]},
            {"name": "Affluent Empty Nesters", "description": "Couples aged 46-60 with grown children, high spending capacity", "size": 95000, "revenue_potential": 52000000.0, "age": "46-60", "gender": "all", "region": "north_america", "income": "high", "tags": ["travel", "luxury", "finance"]},
            {"name": "Budget-Conscious Families", "description": "Families with children, value-oriented shopping behavior", "size": 200000, "revenue_potential": 30000000.0, "age": "36-45", "gender": "all", "region": "all", "income": "middle", "tags": ["family", "groceries", "education"]},
            {"name": "Female Fitness Enthusiasts", "description": "Women aged 18-35 actively engaged in health and wellness", "size": 80000, "revenue_potential": 25000000.0, "age": "18-25", "gender": "female", "region": "all", "income": "middle", "tags": ["fitness", "health", "fashion"]},
            {"name": "Luxury Travelers", "description": "High-net-worth individuals seeking premium travel experiences", "size": 45000, "revenue_potential": 78000000.0, "age": "36-45", "gender": "all", "region": "europe", "income": "luxury", "tags": ["travel", "luxury", "fine_dining"]},
            {"name": "Retirees Abroad", "description": "Retirees aged 60+ living outside their home country", "size": 30000, "revenue_potential": 18000000.0, "age": "60+", "gender": "all", "region": "asia_pacific", "income": "middle", "tags": ["travel", "leisure", "healthcare"]},
        ]
        
        result = []
        for seg in segments_db:
            if age != 'all' and seg['age'] != age:
                continue
            if gender != 'all' and seg['gender'] != gender and seg['gender'] != 'all':
                continue
            if region != 'all' and seg['region'] != region and seg['region'] != 'all':
                continue
            if income != 'all' and seg['income'] != income:
                continue
            if interests:
                if not any(tag.lower() in [i.lower() for i in interests] for tag in seg['tags']):
                    continue
            if seg['size'] < min_size:
                continue
            result.append({
                "name": seg['name'],
                "description": seg['description'],
                "size": seg['size'],
                "revenue_potential": seg['revenue_potential']
            })
        
        result.sort(key=lambda x: x['revenue_potential'], reverse=True)
        return json.dumps({"count": len(result), "segments": result}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "customer_segment_search",
    "description": "Search for customer segments based on demographic, geographic, and behavioral criteria. Returns matching segment names, descriptions, size estimates, and revenue potential for marketing campaign planning.",
    "category": "search",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "age_range": {
            "type": "string",
            "description": "Age range of target customers, e.g., 18-35, 40-60, or 'all' for no filter",
            "enum": [
                "18-25",
                "26-35",
                "36-45",
                "46-60",
                "60+",
                "all"
            ]
        },
        "gender": {
            "type": "string",
            "description": "Gender filter for customer segment",
            "enum": [
                "male",
                "female",
                "non_binary",
                "all"
            ]
        },
        "region": {
            "type": "string",
            "description": "Geographic region to search within, e.g., North America, Europe, Asia Pacific, or 'all'",
            "enum": [
                "north_america",
                "europe",
                "asia_pacific",
                "latin_america",
                "middle_east_africa",
                "all"
            ]
        },
        "income_level": {
            "type": "string",
            "description": "Annual household income bracket for the segment",
            "enum": [
                "low",
                "middle",
                "high",
                "luxury",
                "all"
            ]
        },
        "interests": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of interest keywords to further refine segments, e.g., ['technology', 'travel', 'fitness']"
        },
        "min_segment_size": {
            "type": "integer",
            "description": "Optional: Minimum number of customers in the segment (e.g., 50000)",
            "minimum": 0
        }
    },
    "required": [
        "age_range",
        "gender",
        "region",
        "income_level"
    ]
},
}
