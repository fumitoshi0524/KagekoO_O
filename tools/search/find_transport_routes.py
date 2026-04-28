"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for available transport routes between cities."""
    import json
    try:
        data = json.loads(payload)
        origin = data.get('origin_city', '').strip().title()
        destination = data.get('destination_city', '').strip().title()
        if not origin or not destination:
            return json.dumps({'error': 'origin_city and destination_city are required'})
        # Simulated route database
        routes_db = {
            ('New York', 'Los Angeles'): [
                {'mode': 'flight', 'duration_hours': 6.5, 'price_min': 180, 'price_max': 450, 'transfers': 0},
                {'mode': 'train', 'duration_hours': 48, 'price_min': 120, 'price_max': 300, 'transfers': 1},
                {'mode': 'bus', 'duration_hours': 60, 'price_min': 80, 'price_max': 150, 'transfers': 2}
            ],
            ('Los Angeles', 'New York'): [
                {'mode': 'flight', 'duration_hours': 6.5, 'price_min': 190, 'price_max': 470, 'transfers': 0},
                {'mode': 'train', 'duration_hours': 48, 'price_min': 130, 'price_max': 310, 'transfers': 1}
            ],
            ('London', 'Paris'): [
                {'mode': 'train', 'duration_hours': 2.5, 'price_min': 60, 'price_max': 150, 'transfers': 0},
                {'mode': 'flight', 'duration_hours': 1.5, 'price_min': 100, 'price_max': 250, 'transfers': 0},
                {'mode': 'bus', 'duration_hours': 8, 'price_min': 25, 'price_max': 50, 'transfers': 0}
            ],
            ('Paris', 'London'): [
                {'mode': 'train', 'duration_hours': 2.5, 'price_min': 65, 'price_max': 155, 'transfers': 0},
                {'mode': 'flight', 'duration_hours': 1.5, 'price_min': 105, 'price_max': 260, 'transfers': 0},
                {'mode': 'bus', 'duration_hours': 8, 'price_min': 30, 'price_max': 55, 'transfers': 0}
            ]
        }
        key = (origin, destination)
        routes = routes_db.get(key, [])
        if not routes:
            return json.dumps({'routes': [], 'message': f'No routes found from {origin} to {destination}.'})
        # Filter by preferred mode
        preferred = data.get('preferred_mode', 'any')
        if preferred != 'any':
            routes = [r for r in routes if r['mode'] == preferred]
        # Filter by max transfers
        max_transfers = data.get('max_transfers', 3)
        routes = [r for r in routes if r['transfers'] <= max_transfers]
        if not routes:
            return json.dumps({'routes': [], 'message': 'No routes matching your criteria.'})
        result = {'origin': origin, 'destination': destination, 'routes': routes}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "find_transport_routes",
    "description": "Search for available transportation routes between two locations, returning a list of route options with mode (bus/train/flight), duration, price range, and transfer count for travel planning purposes.",
    "category": "search",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "origin_city": {
            "type": "string",
            "description": "Name of the departure city (e.g., 'New York')."
        },
        "destination_city": {
            "type": "string",
            "description": "Name of the arrival city (e.g., 'Los Angeles')."
        },
        "preferred_mode": {
            "type": "string",
            "enum": [
                "any",
                "bus",
                "train",
                "flight"
            ],
            "description": "Optional: Preferred transportation mode. Use 'any' for no preference."
        },
        "max_transfers": {
            "type": "integer",
            "description": "Optional: Maximum number of transfers allowed (0 for direct routes only). Default is 3.",
            "minimum": 0,
            "maximum": 5
        }
    },
    "required": [
        "origin_city",
        "destination_city"
    ]
},
}
