"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate flight route GeoJSON visualization from origin-destination pairs."""
    import json
    import math

    # Airport coordinate lookup table (subset of major airports)
    AIRPORTS = {
        "JFK": (40.6413, -73.7781), "LAX": (33.9416, -118.4085),
        "LHR": (51.4700, -0.4543), "CDG": (49.0097, 2.5479),
        "DXB": (25.2532, 55.3657), "SIN": (1.3592, 103.9894),
        "HKG": (22.3080, 113.9185), "NRT": (35.7647, 140.3864),
        "SYD": (-33.9461, 151.1772), "FRA": (50.0379, 8.5622),
        "AMS": (52.3105, 4.7683), "IST": (41.2608, 28.7418),
        "ORD": (41.9786, -87.9048), "ATL": (33.6407, -84.4277),
        "PEK": (40.0799, 116.6031), "PVG": (31.1443, 121.8083),
        "SFO": (37.6213, -122.3789), "MIA": (25.7932, -80.2906),
        "BKK": (13.6900, 100.7501), "MEX": (19.4361, -99.0713),
    }

    try:
        data = json.loads(payload)
    except Exception as e:
        return f'error: Invalid JSON payload: {e}'

    routes = data.get("routes")
    if not routes or not isinstance(routes, list) or len(routes) == 0:
        return 'error: "routes" must be a non-empty array'

    # Validate all routes have required fields and known airports
    for i, route in enumerate(routes):
        orig = route.get("origin", "").strip().upper()
        dest = route.get("destination", "").strip().upper()
        if len(orig) != 3 or not orig.isalpha():
            return f'error: route[{i}] origin must be a 3-letter IATA code'
        if len(dest) != 3 or not dest.isalpha():
            return f'error: route[{i}] destination must be a 3-letter IATA code'
        if orig not in AIRPORTS:
            return f'error: Unknown airport code "{orig}" (add to lookup or use a known code)'
        if dest not in AIRPORTS:
            return f'error: Unknown airport code "{dest}" (add to lookup or use a known code)'
        route["origin"] = orig
        route["destination"] = dest

    # Compute great-circle distance if not provided (Haversine formula)
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    # Prepare GeoJSON features
    features = []
    frequencies = []
    distances = []
    durations = []

    for route in routes:
        orig_code = route["origin"]
        dest_code = route["destination"]
        orig_coord = AIRPORTS[orig_code]
        dest_coord = AIRPORTS[dest_code]

        # Compute or use provided distance
        if "distance_km" in route:
            dist = float(route["distance_km"])
        else:
            dist = haversine(orig_coord[0], orig_coord[1], dest_coord[0], dest_coord[1])
        distances.append(dist)

        freq = route.get("frequency", 1)
        frequencies.append(freq)

        dur = route.get("avg_duration_min", 0)
        durations.append(dur)

        # Create arc geometry (simple straight line for now)
        geom = {
            "type": "LineString",
            "coordinates": [
                [orig_coord[1], orig_coord[0]],
                [dest_coord[1], dest_coord[0]]
            ]
        }

        props = {
            "origin": orig_code,
            "destination": dest_code,
            "origin_lat": orig_coord[0],
            "origin_lng": orig_coord[1],
            "destination_lat": dest_coord[0],
            "destination_lng": dest_coord[1],
            "distance_km": round(dist, 1),
            "frequency": freq,
            "airline": route.get("airline", "")
        }

        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": props
        })

    # Determine map center if provided, else compute centroid
    map_center = data.get("map_center")
    if map_center and "lat" in map_center and "lng" in map_center:
        center = (map_center["lat"], map_center["lng"])
    else:
        all_lats = [AIRPORTS[r["origin"]][0] for r in routes] + [AIRPORTS[r["destination"]][0] for r in routes]
        all_lngs = [AIRPORTS[r["origin"]][1] for r in routes] + [AIRPORTS[r["destination"]][1] for r in routes]
        center = (sum(all_lats)/len(all_lats), sum(all_lngs)/len(all_lngs))

    # Get color and width options
    color_by = data.get("color_by", "none")
    line_width_by = data.get("line_width_by", "frequency")

    result = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "total_routes": len(routes),
            "unique_airports": len(set([r["origin"] for r in routes] + [r["destination"] for r in routes])),
            "map_center": {"lat": round(center[0], 4), "lng": round(center[1], 4)},
            "color_by": color_by,
            "line_width_by": line_width_by,
            "generated_at": "2025-04-10T12:00:00Z"
        }
    }

    return json.dumps(result, ensure_ascii=False)


TOOL_SPEC = {
    "name": "flight_route_visualizer",
    "description": "Generate a geographic visualization data object for a set of origin-destination airport pairs, returning a GeoJSON FeatureCollection of flight routes with dynamic line thickness and color based on route frequency, distance, or duration, for use in travel analytics dashboards.",
    "category": "visualization",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "routes": {
            "type": "array",
            "description": "List of flight route objects, each with origin and destination airport IATA codes, and optional metrics",
            "items": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin airport IATA code (3-letter uppercase)",
                        "examples": [
                            "JFK",
                            "LHR"
                        ]
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination airport IATA code (3-letter uppercase)",
                        "examples": [
                            "LAX",
                            "CDG"
                        ]
                    },
                    "frequency": {
                        "type": "integer",
                        "description": "Optional: Number of flights per week on this route; used for line thickness scaling"
                    },
                    "distance_km": {
                        "type": "number",
                        "description": "Optional: Great-circle distance between airports in kilometers; used for color mapping"
                    },
                    "avg_duration_min": {
                        "type": "integer",
                        "description": "Optional: Average flight duration in minutes; used for color mapping if distance not provided"
                    },
                    "airline": {
                        "type": "string",
                        "description": "Optional: Airline code (2-letter IATA) for labeling"
                    }
                },
                "required": [
                    "origin",
                    "destination"
                ]
            },
            "minItems": 1,
            "maxItems": 500
        },
        "map_center": {
            "type": "object",
            "description": "Optional: Center point for map viewport (default: arithmetic center of all route points)",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude in decimal degrees (-90 to 90)"
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude in decimal degrees (-180 to 180)"
                }
            }
        },
        "color_by": {
            "type": "string",
            "description": "Optional: Attribute to color routes by; options: distance, frequency, duration, or none (default: none)",
            "enum": [
                "distance",
                "frequency",
                "duration",
                "none"
            ]
        },
        "line_width_by": {
            "type": "string",
            "description": "Optional: Attribute to scale line width by; options: frequency, distance, duration, or none (default: frequency)",
            "enum": [
                "frequency",
                "distance",
                "duration",
                "none"
            ]
        }
    },
    "required": [
        "routes"
    ]
},
}
