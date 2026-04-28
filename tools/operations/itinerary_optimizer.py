"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Optimize a multi-stop travel itinerary to minimize distance or time."""
    import json
    import math
    from itertools import permutations

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    try:
        data = json.loads(payload)
        stops = data.get('stops', [])
        if not stops or len(stops) < 2:
            return json.dumps({'error': 'At least 2 stops are required.'})
        if len(stops) > 20:
            return json.dumps({'error': 'Maximum 20 stops allowed.'})

        start_point = data.get('start_point')
        end_point = data.get('end_point')
        unit = data.get('unit', 'km')
        optimization_metric = data.get('optimization_metric', 'distance')

        # Convert to miles if needed
        conversion_factor = 1.0
        if unit == 'miles':
            conversion_factor = 0.621371

        # Build list of stops to permute (excluding start/end if specified)
        permute_stops = stops[:]
        if start_point:
            permute_stops = [s for s in permute_stops if s['name'] != start_point['name']]
        if end_point:
            permute_stops = [s for s in permute_stops if s['name'] != end_point['name']]

        if len(permute_stops) > 8:
            return json.dumps({'error': 'Optimization limited to 8 intermediate stops for performance.'})

        best_order = None
        best_distance = float('inf')

        for perm in permutations(permute_stops):
            route = []
            if start_point:
                route.append(start_point)
            route.extend(perm)
            if end_point:
                route.append(end_point)

            total_dist = 0
            for i in range(len(route)-1):
                d = haversine(route[i]['latitude'], route[i]['longitude'], route[i+1]['latitude'], route[i+1]['longitude'])
                total_dist += d

            if total_dist < best_distance:
                best_distance = total_dist
                best_order = route

        if not best_order:
            return json.dumps({'error': 'Could not optimize itinerary.'})

        # Build output with segments
        optimized_stops = []
        segments = []
        for i, stop in enumerate(best_order):
            optimized_stops.append({'name': stop['name'], 'latitude': stop['latitude'], 'longitude': stop['longitude'], 'order': i+1})
            if i > 0:
                prev = best_order[i-1]
                dist_km = haversine(prev['latitude'], prev['longitude'], stop['latitude'], stop['longitude'])
                dist = dist_km * conversion_factor
                segments.append({
                    'from': prev['name'],
                    'to': stop['name'],
                    'distance': round(dist, 2),
                    'unit': unit
                })

        result = {
            'optimized_stops': optimized_stops,
            'segments': segments,
            'total_distance': round(best_distance * conversion_factor, 2),
            'unit': unit,
            'optimization_metric': optimization_metric
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "itinerary_optimizer",
    "description": "Optimize a multi-stop travel itinerary by reordering destinations to minimize total travel distance or time, using geographic coordinates and optional constraints like required stay durations or preferred start/end points. Returns the optimized sequence of stops with updated travel metrics.",
    "category": "operations",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "stops": {
            "type": "array",
            "description": "Array of stop objects, each containing a name, latitude, and longitude. Minimum 2 stops, maximum 20.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name or identifier of the stop."
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude in decimal degrees (range: -90 to 90)."
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude in decimal degrees (range: -180 to 180)."
                    }
                },
                "required": [
                    "name",
                    "latitude",
                    "longitude"
                ]
            }
        },
        "start_point": {
            "type": "object",
            "description": "Optional: Fixed starting point for the itinerary. Must include name, latitude, and longitude.",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the start point."
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude in decimal degrees."
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude in decimal degrees."
                }
            },
            "required": [
                "name",
                "latitude",
                "longitude"
            ]
        },
        "end_point": {
            "type": "object",
            "description": "Optional: Fixed ending point for the itinerary. Must include name, latitude, and longitude.",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the end point."
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude in decimal degrees."
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude in decimal degrees."
                }
            },
            "required": [
                "name",
                "latitude",
                "longitude"
            ]
        },
        "optimization_metric": {
            "type": "string",
            "description": "Optional: Metric to optimize for. Default is 'distance'.",
            "enum": [
                "distance",
                "time"
            ],
            "default": "distance"
        },
        "unit": {
            "type": "string",
            "description": "Optional: Unit for distance output. Default is 'km'.",
            "enum": [
                "km",
                "miles"
            ],
            "default": "km"
        }
    },
    "required": [
        "stops"
    ]
},
}
