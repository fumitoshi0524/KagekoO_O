"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        destination = data.get('destination')
        num_days = data.get('num_days')
        travel_style = data.get('travel_style')
        budget_level = data.get('budget_level')
        interests = data.get('interests', [])
        if not destination or not isinstance(destination, str):
            return json.dumps({'error': 'Invalid or missing destination'}, ensure_ascii=False)
        if not isinstance(num_days, int) or num_days < 1 or num_days > 30:
            return json.dumps({'error': 'num_days must be an integer between 1 and 30'}, ensure_ascii=False)
        valid_styles = ['adventure', 'culture', 'relaxation', 'luxury', 'budget', 'family']
        if travel_style not in valid_styles:
            return json.dumps({'error': f'Invalid travel_style. Must be one of {valid_styles}'}, ensure_ascii=False)
        valid_budgets = ['low', 'medium', 'high']
        if budget_level not in valid_budgets:
            return json.dumps({'error': f'Invalid budget_level. Must be one of {valid_budgets}'}, ensure_ascii=False)
        # Build itinerary
        activities_pool = {
            'adventure': ['Zip-lining', 'White-water rafting', 'Rock climbing', 'Bungee jumping', 'Scuba diving', 'Paragliding'],
            'culture': ['Visit museums', 'Attend local festivals', 'Explore temples', 'Art galleries', 'Traditional performances'],
            'relaxation': ['Spa day', 'Beach lounging', 'Yoga retreat', 'Sunset cruises', 'Hot springs'],
            'luxury': ['Private tours', 'Fine dining', 'Helicopter rides', 'Luxury shopping', 'VIP experiences'],
            'budget': ['Free walking tours', 'Street food', 'Hiking', 'Public parks', 'Budget hostels'],
            'family': ['Amusement parks', 'Zoo', 'Aquarium', 'Kid-friendly museums', 'Boat rides']
        }
        dining_options = ['Local cuisine restaurant', 'Street food market', 'Cafe with view', 'Family-friendly diner', 'Rooftop bar', 'Seafood grill']
        itinerary = {}
        for day in range(1, num_days + 1):
            morning_activities = [activities_pool[travel_style][i % len(activities_pool[travel_style])] for i in range(day * 3 - 3, day * 3 - 2)]
            afternoon_activities = [activities_pool[travel_style][i % len(activities_pool[travel_style])] for i in range(day * 3 - 2, day * 3 - 1)]
            evening_activities = [activities_pool[travel_style][i % len(activities_pool[travel_style])] for i in range(day * 3 - 1, day * 3)]
            dining = dining_options[(day - 1) % len(dining_options)]
            # Incorporate interests if provided
            if interests:
                interest_activity = interests[(day - 1) % len(interests)]
                evening_activities.append(f'Special interest: {interest_activity}')
            itinerary[f'day_{day}'] = {
                'morning': morning_activities,
                'afternoon': afternoon_activities,
                'evening': evening_activities,
                'dining_suggestion': dining
            }
        result = {
            'destination': destination,
            'num_days': num_days,
            'travel_style': travel_style,
            'budget_level': budget_level,
            'itinerary': itinerary,
            'budget_estimate': f'Estimated total cost (per person): {{"low": "$500-1000", "medium": "$1000-3000", "high": "$3000+"}.get(budget_level, "unknown")}'
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "itinerary_generator",
    "description": "Generate a personalized multi-day travel itinerary for a destination based on user preferences including travel style, budget level, and interests, returning a structured day-by-day plan with recommended attractions, dining options, and activities.",
    "category": "generate",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "destination": {
            "type": "string",
            "description": "City or region name for the trip (e.g., 'Paris', 'Tokyo', 'Bali')."
        },
        "num_days": {
            "type": "integer",
            "description": "Number of days for the itinerary, between 1 and 30."
        },
        "travel_style": {
            "type": "string",
            "enum": [
                "adventure",
                "culture",
                "relaxation",
                "luxury",
                "budget",
                "family"
            ],
            "description": "Preferred travel style to tailor activities and pace."
        },
        "budget_level": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high"
            ],
            "description": "Budget level for accommodation and activities."
        },
        "interests": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "museums",
                    "food",
                    "shopping",
                    "nature",
                    "history",
                    "nightlife",
                    "beaches",
                    "hiking",
                    "architecture",
                    "local_experiences"
                ]
            },
            "description": "Optional: List of specific interests to prioritize (max 5).",
            "maxItems": 5
        }
    },
    "required": [
        "destination",
        "num_days",
        "travel_style",
        "budget_level"
    ]
},
}
