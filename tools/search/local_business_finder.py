"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for local businesses and services by category, location, and rating."""
    import json
    import random
    import math

    try:
        data = json.loads(payload)
        query = data.get('query', '').strip()
        location = data.get('location', '').strip()
        if not query:
            return json.dumps({'error': 'query is required'}, ensure_ascii=False)
        if not location:
            return json.dumps({'error': 'location is required'}, ensure_ascii=False)

        radius_km = data.get('radius_km', 5)
        if radius_km < 1 or radius_km > 50:
            radius_km = 5

        min_rating = data.get('min_rating')
        if min_rating is not None and (min_rating < 1.0 or min_rating > 5.0):
            min_rating = None

        max_results = data.get('max_results', 10)
        if max_results < 1 or max_results > 50:
            max_results = 10

        # Seed random based on query + location for consistent results
        seed = hash(query.lower() + location.lower() + str(radius_km)) % (2**31)
        rng = random.Random(seed)

        business_types = {
            'restaurant': ['Italian Bistro', 'Sushi House', 'Burger Joint', 'Taco Stand', 'Pizza Place', 'Thai Kitchen', 'Indian Curry House', 'French Bakery', 'Greek Taverna', 'Vietnamese Pho'],
            'cafe': ['Morning Brew', 'Bean & Leaf', 'Caffeine Corner', 'The Roasted Bean', 'Cozy Cup Cafe', 'Espresso Express'],
            'salon': ['Glamour Cuts', 'Style Studio', 'Barber Pro', 'Beauty Lounge', 'Hair Haven', 'Nail & Spa'],
            'gym': ['FitZone', 'Iron Paradise', 'Pulse Fitness', 'StrongBody Gym', 'Zen Yoga Studio', 'CrossFit Box'],
            'pharmacy': ['HealthPlus Pharmacy', 'MediCare Drugs', 'City Pharmacy', 'Wellness Rx'],
            'grocery': ['Fresh Market', 'Green Grocer', 'City Mart', 'Organic Delights'],
            'laundry': ['Wash & Go', 'CleanPress Laundry', 'Bubble Wash'],
            'auto': ['Quick Fix Auto', 'Speedy Service', 'Auto Care Center']
        }

        # Determine category from query
        query_lower = query.lower()
        category = 'general'
        for cat, keywords in {
            'restaurant': ['restaurant', 'pizza', 'sushi', 'burger', 'taco', 'thai', 'indian', 'french', 'greek', 'vietnamese', 'food', 'dinner', 'lunch', 'breakfast'],
            'cafe': ['cafe', 'coffee', 'tea', 'bakery', 'pastry', 'brew'],
            'salon': ['salon', 'hair', 'barber', 'beauty', 'nail', 'spa', 'cut', 'style'],
            'gym': ['gym', 'fitness', 'workout', 'yoga', 'pilates', 'crossfit', 'exercise'],
            'pharmacy': ['pharmacy', 'drugs', 'medication', 'prescription', 'chemist'],
            'grocery': ['grocery', 'market', 'supermarket', 'food store', 'produce'],
            'laundry': ['laundry', 'dry cleaning', 'wash', 'cleaner'],
            'auto': ['auto', 'car', 'mechanic', 'garage', 'repair']
        }.items():
            if any(kw in query_lower for kw in keywords):
                category = cat
                break

        # Generate businesses
        names = business_types.get(category, ['Local Business', 'City Service', 'Neighborhood Shop', 'Downtown Store', 'Main Street Services'])
        results = []
        num_results = min(max_results, rng.randint(3, len(names)))

        # Generate coordinates based on location hash
        lat_base = (seed % 180) - 90
        lng_base = (seed // 180 % 360) - 180

        for i in range(num_results):
            name = names[i % len(names)]
            if category == 'general':
                name = f"{name} #{i+1}"
            
            # Generate realistic phone number
            area = rng.randint(200, 999)
            prefix = rng.randint(200, 999)
            line = rng.randint(1000, 9999)
            phone = f"({area}) {prefix}-{line}"
            
            # Generate rating (weighted toward higher ratings)
            rating = round(min(5.0, max(1.0, rng.gauss(4.0, 0.8))), 1)
            
            # Apply min_rating filter
            if min_rating is not None and rating < min_rating:
                rating = max(min_rating, round(rng.uniform(min_rating, 5.0), 1))
            
            # Calculate approximate distance from center
            lat_offset = rng.uniform(-0.5, 0.5) * (radius_km / 111.0)
            lng_offset = rng.uniform(-0.5, 0.5) * (radius_km / 111.0) / math.cos(math.radians(lat_base))
            distance_km = round(math.sqrt(lat_offset**2 + lng_offset**2) * 111.0, 1)
            
            # Generate opening hours
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            hours = {}
            for day in days:
                if rng.random() > 0.1:  # 90% chance open
                    open_h = rng.choice([7, 8, 9, 10, 11])
                    close_h = rng.choice([17, 18, 19, 20, 21, 22])
                    if close_h <= open_h:
                        close_h = open_h + 8
                    hours[day] = f"{open_h:02d}:00-{close_h:02d}:00"
                else:
                    hours[day] = "Closed"
            
            business = {
                'name': name,
                'address': f"{rng.randint(100, 9999)} {rng.choice(['Main', 'Oak', 'Elm', 'Park', 'Broadway', 'Market', 'River', 'Lake']) } {rng.choice(['St', 'Ave', 'Blvd', 'Rd', 'Dr', 'Ln']) },",
                'phone': phone,
                'rating': rating,
                'distance_km': distance_km,
                'opening_hours': hours,
                'category': category,
                'price_level': rng.choice(['$', '$$', '$$$']),
                'open_now': hours.get('Monday', 'Closed') != 'Closed' and rng.random() > 0.3
            }
            results.append(business)

        # Sort by rating (descending), then distance
        results.sort(key=lambda x: (-x['rating'], x['distance_km']))

        response = {
            'query': query,
            'location': location,
            'radius_km': radius_km,
            'total_results': len(results),
            'results': results[:max_results],
            'search_metadata': {
                'category_detected': category,
                'seed': seed
            }
        }

        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "local_business_finder",
    "description": "Search for local businesses and services (restaurants, salons, gyms, etc.) by category, location, and rating. Returns a list of matching businesses with name, address, phone, rating, and opening hours for planning daily errands or outings.",
    "category": "search",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search term for the type of business or service needed, e.g., 'pizza', 'hair salon', 'gym'",
            "examples": [
                "pizza",
                "hair salon",
                "coffee shop"
            ]
        },
        "location": {
            "type": "string",
            "description": "Address, city, or zip code to search near",
            "examples": [
                "New York, NY",
                "10001",
                "221B Baker Street, London"
            ]
        },
        "radius_km": {
            "type": "number",
            "description": "Optional: Search radius in kilometers (default 5, max 50)",
            "minimum": 1,
            "maximum": 50,
            "default": 5
        },
        "min_rating": {
            "type": "number",
            "description": "Optional: Minimum average rating filter (1.0 to 5.0)",
            "minimum": 1.0,
            "maximum": 5.0
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (default 10, max 50)",
            "minimum": 1,
            "maximum": 50,
            "default": 10
        }
    },
    "required": [
        "query",
        "location"
    ]
},
}
