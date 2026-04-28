"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    import random
    try:
        data = json.loads(payload)
        lat = data['latitude']
        lon = data['longitude']
        radius = data['radius_km']
        min_risk = data.get('min_risk_level', 'moderate')
        include_history = data.get('include_history', False)

        if not (-90 <= lat <= 90):
            return json.dumps({'error': 'Latitude must be between -90 and 90'})
        if not (-180 <= lon <= 180):
            return json.dumps({'error': 'Longitude must be between -180 and 180'})
        if not (1 <= radius <= 500):
            return json.dumps({'error': 'Radius must be between 1 and 500 km'})

        risk_levels = ['low', 'moderate', 'high', 'extreme']
        min_idx = risk_levels.index(min_risk) if min_risk in risk_levels else 1

        # Simulate realistic risk zone detection based on pseudo-random factors
        random.seed(hash((lat, lon, radius)) % 100000)
        num_zones = random.randint(1, 5)
        zones = []
        for i in range(num_zones):
            # Generate zone center within radius
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, radius)
            delta_lat = (dist / 111.32) * math.cos(angle)
            delta_lon = (dist / (111.32 * math.cos(math.radians(lat)))) * math.sin(angle)
            zone_lat = round(lat + delta_lat, 4)
            zone_lon = round(lon + delta_lon, 4)

            # Assign risk level weighted by proximity to center and random factors
            risk_idx = random.randint(min_idx, 3)
            risk_level = risk_levels[risk_idx]

            # Size proportional to risk
            size_km2 = round(random.uniform(10, 200) * (risk_idx + 1), 2)

            zone = {
                'zone_id': f'WFZ-{lat:.1f}-{lon:.1f}-{i+1}',
                'latitude': zone_lat,
                'longitude': zone_lon,
                'risk_level': risk_level,
                'area_km2': size_km2,
                'distance_from_center_km': round(dist, 2),
                'vegetation_index': round(random.uniform(0.3, 0.9), 2),
                'temperature_c': round(random.uniform(15, 45), 1),
                'humidity_pct': round(random.uniform(10, 60), 1),
                'wind_speed_kmh': round(random.uniform(5, 50), 1)
            }
            if include_history:
                zone['recent_fires'] = random.randint(0, min(10, risk_idx * 3))
            zones.append(zone)

        result = {
            'status': 'success',
            'search_center': {'latitude': lat, 'longitude': lon},
            'radius_km': radius,
            'risk_zones_count': len(zones),
            'highest_risk_found': max(z['risk_level'] for z in zones) if zones else 'none',
            'risk_zones': zones
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Invalid input: {str(e)}'})


TOOL_SPEC = {
    "name": "find_wildfire_risk_zones",
    "description": "Search for geographic areas with elevated wildfire risk based on weather conditions, vegetation index, and historical fire data to support environmental monitoring and disaster preparedness planning.",
    "category": "search",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "latitude": {
            "type": "number",
            "description": "Center latitude of the search area (WGS84, range -90 to 90)",
            "minimum": -90,
            "maximum": 90
        },
        "longitude": {
            "type": "number",
            "description": "Center longitude of the search area (WGS84, range -180 to 180)",
            "minimum": -180,
            "maximum": 180
        },
        "radius_km": {
            "type": "number",
            "description": "Search radius in kilometers from center point (range 1 to 500)",
            "minimum": 1,
            "maximum": 500
        },
        "min_risk_level": {
            "type": "string",
            "description": "Optional: Minimum risk level to filter results (default 'moderate')",
            "enum": [
                "low",
                "moderate",
                "high",
                "extreme"
            ],
            "default": "moderate"
        },
        "include_history": {
            "type": "boolean",
            "description": "Optional: Whether to include historical fire incident data in the results (default false)",
            "default": false
        }
    },
    "required": [
        "latitude",
        "longitude",
        "radius_km"
    ]
},
}
