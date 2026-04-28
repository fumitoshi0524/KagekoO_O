"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a visual map-style representation of a multi-stop travel itinerary showing the route connections, stop order, and cumulative distance between consecutive points on a journey."""
    import json
    import math
    try:
        data = json.loads(payload)
        stops = data.get('stops')
        if not stops or len(stops) < 2:
            return 'error: At least 2 stops are required'
        
        route_color = data.get('route_color', '#2563EB')
        map_style = data.get('map_style', 'roadmap')
        return_format = data.get('return_format', 'svg')
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth radius in km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            c = 2 * math.asin(min(1, math.sqrt(a)))
            return round(R * c, 1)
        
        # Calculate cumulative distances and build segments
        segments = []
        total_distance = 0
        for i in range(len(stops) - 1):
            s1 = stops[i]
            s2 = stops[i+1]
            dist = haversine(s1['latitude'], s1['longitude'], s2['latitude'], s2['longitude'])
            total_distance += dist
            segments.append({
                'from_index': i,
                'to_index': i+1,
                'from_name': s1['name'],
                'to_name': s2['name'],
                'distance_km': dist,
                'cumulative_distance_km': round(total_distance, 1)
            })
        
        if return_format == 'json_data':
            result = {
                'stops': [{'name': s['name'], 'latitude': s['latitude'], 'longitude': s['longitude'], 'stop_type': s.get('stop_type', 'custom')} for s in stops],
                'segments': segments,
                'total_distance_km': round(total_distance, 1),
                'number_of_stops': len(stops),
                'route_color': route_color,
                'map_style': map_style
            }
            return json.dumps(result, ensure_ascii=False)
        
        # SVG generation (simplified flat representation)
        svg_width = 800
        svg_height = 400
        padding = 40
        
        # Normalize coordinates
        lats = [s['latitude'] for s in stops]
        lons = [s['longitude'] for s in stops]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        lat_range = max_lat - min_lat if max_lat != min_lat else 1
        lon_range = max_lon - min_lon if max_lon != min_lon else 1
        
        def to_svg_coords(lat, lon):
            x = padding + (lon - min_lon) / lon_range * (svg_width - 2*padding)
            y = svg_height - padding - (lat - min_lat) / lat_range * (svg_height - 2*padding)
            return x, y
        
        points = [to_svg_coords(s['latitude'], s['longitude']) for s in stops]
        
        # Build path data
        path_d = f'M {points[0][0]} {points[0][1]}'
        for p in points[1:]:
            path_d += f' L {p[0]} {p[1]}'
        
        # Stop marker colors
        type_colors = {
            'city': '#3B82F6',
            'attraction': '#F59E0B',
            'accommodation': '#10B981',
            'transit_hub': '#8B5CF6',
            'custom': '#6B7280'
        }
        
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
            f'<rect width="100%" height="100%" fill="#F9FAFB" rx="8"/>',
            f'<path d="{path_d}" stroke="{route_color}" stroke-width="3" fill="none" stroke-linejoin="round" stroke-linecap="round"/>'
        ]
        
        # Add segment distances and stop markers
        for i, (x, y) in enumerate(points):
            # Stop circle
            stop_type = stops[i].get('stop_type', 'custom')
            fill = type_colors.get(stop_type, '#6B7280')
            svg_parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{fill}" stroke="white" stroke-width="2"/>')
            svg_parts.append(f'<text x="{x}" y="{y-12}" text-anchor="middle" font-size="11" font-family="Arial" fill="#374151">{stops[i]["name"]}</text>')
            svg_parts.append(f'<text x="{x}" y="{y+20}" text-anchor="middle" font-size="9" font-family="Arial" fill="#9CA3AF">#{i+1}</text>')
            
            # Add distance labels on segments
            if i < len(points) - 1:
                mid_x = (x + points[i+1][0]) / 2
                mid_y = (y + points[i+1][1]) / 2 - 15
                dist_text = f'{segments[i]["distance_km"]} km'
                svg_parts.append(f'<rect x="{mid_x-25}" y="{mid_y-8}" width="50" height="16" rx="4" fill="{route_color}20"/>')
                svg_parts.append(f'<text x="{mid_x}" y="{mid_y+3}" text-anchor="middle" font-size="9" font-family="Arial" fill="{route_color}">{dist_text}</text>')
        
        # Legend
        legend_y = 20
        svg_parts.append(f'<text x="20" y="{legend_y}" font-size="12" font-family="Arial" font-weight="bold" fill="#374151">Route Visualization</text>')
        
        svg_parts.append(f'<text x="20" y="{legend_y+20}" font-size="10" font-family="Arial" fill="#6B7280">Stops: {len(stops)} | Total Distance: {round(total_distance, 1)} km</text>')
        svg_parts.append('</svg>')
        
        result = {
            'svg': '\n'.join(svg_parts),
            'total_distance_km': round(total_distance, 1),
            'number_of_segments': len(segments),
            'stops_summary': [{'name': s['name'], 'type': s.get('stop_type', 'custom')} for s in stops]
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "itinerary_route_visualizer",
    "description": "Generate a visual map-style representation of a multi-stop travel itinerary showing the route connections, stop order, and cumulative distance between consecutive points on a journey.",
    "category": "visualization",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "stops": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the stop (city, landmark, or accommodation)"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the stop in decimal degrees"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the stop in decimal degrees"
                    },
                    "stop_type": {
                        "type": "string",
                        "enum": [
                            "city",
                            "attraction",
                            "accommodation",
                            "transit_hub",
                            "custom"
                        ],
                        "description": "Category of the stop to determine marker style"
                    }
                },
                "required": [
                    "name",
                    "latitude",
                    "longitude"
                ]
            },
            "description": "Ordered list of stops along the journey, from start to finish"
        },
        "route_color": {
            "type": "string",
            "description": "Optional: Hex color code for the route line (e.g., '#FF5733'). Default is '#2563EB'"
        },
        "map_style": {
            "type": "string",
            "enum": [
                "roadmap",
                "terrain",
                "satellite",
                "retro"
            ],
            "description": "Optional: Visual style of the map background. Default is 'roadmap'"
        },
        "return_format": {
            "type": "string",
            "enum": [
                "svg",
                "json_data"
            ],
            "description": "Optional: Output format. 'svg' returns an inline SVG map, 'json_data' returns structured coordinates and metadata. Default is 'svg'"
        }
    },
    "required": [
        "stops"
    ]
},
}
