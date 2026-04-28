"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        dest = data.get('destination')
        days = data.get('duration_days')
        style = data.get('travel_style')
        if not dest or not days or not style:
            return json.dumps({'error': 'Missing required fields: destination, duration_days, travel_style'})
        if days < 1:
            return json.dumps({'error': 'duration_days must be at least 1'})
        num = data.get('num_travelers', 1)
        if num < 1:
            return json.dumps({'error': 'num_travelers must be at least 1'})
        # Default cost estimates per person per day based on style (USD)
        base_costs = {
            'budget': {'hotel': 50, 'meals': 30, 'activities': 20, 'transport': 10, 'flight': 300},
            'standard': {'hotel': 120, 'meals': 60, 'activities': 40, 'transport': 20, 'flight': 500},
            'luxury': {'hotel': 300, 'meals': 150, 'activities': 100, 'transport': 50, 'flight': 1000}
        }
        costs = base_costs.get(style, base_costs['standard'])
        # Override with provided values if present
        flight_total = data.get('flight_cost', costs['flight']) * num
        hotel_nightly = data.get('hotel_nightly_rate', costs['hotel'])
        hotel_total = hotel_nightly * days * num
        meals_daily = data.get('meals_daily_budget', costs['meals'])
        meals_total = meals_daily * days * num
        activities_daily = data.get('activities_daily_budget', costs['activities'])
        activities_total = activities_daily * days * num
        transport_daily = data.get('transport_daily_budget', costs['transport'])
        transport_total = transport_daily * days * num
        rental_car_daily = data.get('rental_car_daily_rate', 0)
        rental_car_total = rental_car_daily * days  # per vehicle, not per person
        grand_total = flight_total + hotel_total + meals_total + activities_total + transport_total + rental_car_total
        result = {
            'destination': dest,
            'duration_days': days,
            'travel_style': style,
            'num_travelers': num,
            'currency': data.get('currency', 'USD'),
            'flight_cost': round(flight_total, 2),
            'hotel_cost': round(hotel_total, 2),
            'meals_cost': round(meals_total, 2),
            'activities_cost': round(activities_total, 2),
            'local_transport_cost': round(transport_total, 2),
            'rental_car_cost': round(rental_car_total, 2),
            'grand_total': round(grand_total, 2)
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})



TOOL_SPEC = {
    "name": "trip_cost_estimator",
    "description": "Estimate total trip cost including flights, hotels, rental cars, meals, and activities based on user inputs such as destination, duration, and travel style, returning a detailed cost breakdown and grand total.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "destination": {
            "type": "string",
            "description": "City or region name for the trip destination."
        },
        "duration_days": {
            "type": "integer",
            "description": "Number of days for the trip, must be at least 1.",
            "minimum": 1
        },
        "travel_style": {
            "type": "string",
            "enum": [
                "budget",
                "standard",
                "luxury"
            ],
            "description": "Travel style category affecting cost multipliers."
        },
        "currency": {
            "type": "string",
            "description": "Optional: Three-letter currency code for output (e.g., USD, EUR). Default is USD.",
            "default": "USD"
        },
        "flight_cost": {
            "type": "number",
            "description": "Optional: Estimated round-trip flight cost per person in the chosen currency. If omitted, a default estimate based on destination and travel style is used.",
            "minimum": 0
        },
        "hotel_nightly_rate": {
            "type": "number",
            "description": "Optional: Estimated hotel cost per night in the chosen currency. If omitted, a default estimate based on travel style is used.",
            "minimum": 0
        },
        "meals_daily_budget": {
            "type": "number",
            "description": "Optional: Estimated daily meal cost per person in the chosen currency. If omitted, a default estimate based on travel style is used.",
            "minimum": 0
        },
        "activities_daily_budget": {
            "type": "number",
            "description": "Optional: Estimated daily cost for activities and attractions per person in the chosen currency. If omitted, a default estimate based on travel style is used.",
            "minimum": 0
        },
        "transport_daily_budget": {
            "type": "number",
            "description": "Optional: Estimated daily local transportation cost per person (excluding rental car) in the chosen currency. If omitted, a default estimate based on travel style is used.",
            "minimum": 0
        },
        "rental_car_daily_rate": {
            "type": "number",
            "description": "Optional: Estimated daily rental car cost in the chosen currency. If omitted, no rental car cost is added.",
            "minimum": 0
        },
        "num_travelers": {
            "type": "integer",
            "description": "Optional: Number of travelers for the trip. Default is 1.",
            "minimum": 1,
            "default": 1
        }
    },
    "required": [
        "destination",
        "duration_days",
        "travel_style"
    ]
},
}
