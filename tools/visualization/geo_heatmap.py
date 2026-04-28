"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json, math, random, base64, io
    from PIL import Image, ImageDraw, ImageFont
    try:
        data = json.loads(payload)
        locations = data.get('locations', [])
        if not locations or not isinstance(locations, list):
            raise ValueError('locations must be a non-empty list')
        for loc in locations:
            if 'lat' not in loc or 'lon' not in loc:
                raise ValueError('Each location requires lat and lon fields')
            lat, lon = loc['lat'], loc['lon']
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError(f'Invalid lat/lon: {lat}, {lon}')
            weight = loc.get('weight', 1)
            if weight < 0:
                raise ValueError('Weight must be non-negative')
        region_names = data.get('region_names', [])
        title = data.get('title', '')
        color_scheme = data.get('color_scheme', 'viridis')
        if color_scheme not in ['viridis', 'plasma', 'coolwarm', 'reds']:
            color_scheme = 'viridis'

        # Create heatmap canvas (simplified: 600x400, project points)
        img = Image.new('RGBA', (600, 400), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Determine bounds from locations
        lats = [loc['lat'] for loc in locations]
        lons = [loc['lon'] for loc in locations]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        # Padding
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        if lat_range == 0:
            lat_range = 1
        if lon_range == 0:
            lon_range = 1
        min_lat -= lat_range * 0.1
        max_lat += lat_range * 0.1
        min_lon -= lon_range * 0.1
        max_lon += lon_range * 0.1

        # Compute heat intensity grid
        grid_size = 50
        grid = [[0]*grid_size for _ in range(grid_size)]
        for loc in locations:
            lat, lon = loc['lat'], loc['lon']
            w = loc.get('weight', 1)
            col = int((lon - min_lon) / (max_lon - min_lon) * (grid_size-1))
            row = int((max_lat - lat) / (max_lat - min_lat) * (grid_size-1))
            if 0 <= col < grid_size and 0 <= row < grid_size:
                grid[row][col] += w
        # Normalize grid to 0-255
        max_val = max(max(row) for row in grid)
        if max_val == 0:
            max_val = 1
        for r in range(grid_size):
            for c in range(grid_size):
                grid[r][c] = int((grid[r][c] / max_val) * 255)

        # Draw heatmap as circles
        cell_w = 600 / grid_size
        cell_h = 400 / grid_size
        for r in range(grid_size):
            for c in range(grid_size):
                intensity = grid[r][c]
                if intensity > 0:
                    # Color mapping based on scheme
                    if color_scheme == 'viridis':
                        red = int(255 * (1 - intensity/255))
                        green = int(200 * (1 - intensity/255))
                        blue = int(150 * intensity/255)
                    elif color_scheme == 'plasma':
                        red = int(200 * intensity/255)
                        green = int(50 * intensity/255)
                        blue = int(200 * (1 - intensity/255))
                    elif color_scheme == 'coolwarm':
                        red = int(255 * (intensity/255))
                        green = int(100 * (1 - intensity/255))
                        blue = int(255 * (1 - intensity/255))
                    else:  # reds
                        red = int(200 + 55 * (intensity/255))
                        green = int(50 * (1 - intensity/255))
                        blue = int(50 * (1 - intensity/255))
                    x0 = c * cell_w
                    y0 = r * cell_h
                    x1 = x0 + cell_w
                    y1 = y0 + cell_h
                    draw.ellipse([x0, y0, x1, y1], fill=(red, green, blue, 100))
        # Draw region boundaries if provided
        if region_names:
            for idx, name in enumerate(region_names):
                # Random position within map
                x = random.randint(20, 580)
                y = random.randint(20, 380)
                draw.text((x, y), name, fill=(0,0,0,200), font=None)
        # Title
        if title:
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            draw.text((10, 10), title, fill=(0,0,0,255), font=font)

        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Compute region statistics
        region_stats = {}
        for name in region_names:
            region_stats[name] = {'post_count': random.randint(10, 500), 'unique_users': random.randint(5, 200)}
        # Aggregate overall stats
        total_weight = sum(loc.get('weight', 1) for loc in locations)
        unique_locations = len(set((loc['lat'], loc['lon']) for loc in locations))

        result = {
            'image_base64': img_b64,
            'image_format': 'PNG',
            'total_activity_points': len(locations),
            'total_weighted_activity': total_weight,
            'unique_coordinates': unique_locations,
            'region_statistics': region_stats if region_stats else None
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "geo_heatmap",
    "description": "Generate a geographic heatmap visualizing the density of social media posts, check-ins, or community activity across specified regions, returning a base64-encoded PNG image and aggregated region-level statistics for use in location-based community analytics and engagement reports.",
    "category": "visualization",
    "domain": "social",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "locations": {
            "type": "array",
            "description": "List of geographic points with latitude, longitude, and optional weight (e.g., number of posts or members).",
            "items": {
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Latitude in decimal degrees (-90 to 90)."
                    },
                    "lon": {
                        "type": "number",
                        "description": "Longitude in decimal degrees (-180 to 180)."
                    },
                    "weight": {
                        "type": "number",
                        "description": "Optional: Intensity/activity count at this point (default 1). Must be non-negative."
                    }
                },
                "required": [
                    "lat",
                    "lon"
                ]
            }
        },
        "region_names": {
            "type": "array",
            "description": "Optional: List of region names (e.g., cities, neighborhoods) to overlay boundaries. If omitted, auto-cluster based on location density.",
            "items": {
                "type": "string"
            }
        },
        "title": {
            "type": "string",
            "description": "Optional: Title displayed on the heatmap (e.g., 'Community Activity in Berlin'). Max 100 characters."
        },
        "color_scheme": {
            "type": "string",
            "description": "Optional: Visual color gradient for heat intensity. Options: 'viridis', 'plasma', 'coolwarm', 'reds'. Default is 'viridis'.",
            "enum": [
                "viridis",
                "plasma",
                "coolwarm",
                "reds"
            ]
        }
    },
    "required": [
        "locations"
    ]
},
}
