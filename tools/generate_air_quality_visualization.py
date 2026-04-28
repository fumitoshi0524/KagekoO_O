"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate an air quality visualization overlay."""
    import json
    import base64
    from datetime import datetime

    try:
        data = json.loads(payload)
        region = data.get('region')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        pollutants = data.get('pollutants', ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co'])
        map_style = data.get('map_style', 'street')
        output_format = data.get('output_format', 'png_base64')
        
        if not region:
            return json.dumps({'error': 'Region is required.'})
        if not start_date or not end_date:
            return json.dumps({'error': 'Both start_date and end_date are required.'})
        
        # Validate dates
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Dates must be in YYYY-MM-DD format.'})
        
        if start_date > end_date:
            return json.dumps({'error': 'start_date must be before end_date.'})
        
        # Simulate fetching AQI data and generating a visualization
        # In production, this would query a real air quality API (e.g., OpenAQ, WAQI)
        # and use a mapping library (e.g., Folium, Matplotlib) to create the overlay.
        
        # Placeholder for real data fetching and rendering
        aqi_data = {
            'region': region,
            'start_date': start_date,
            'end_date': end_date,
            'pollutants_analyzed': pollutants,
            'avg_aqi': 45,
            'max_aqi': 120,
            'category': 'Moderate'
        }
        
        # Generate a dummy base64 image (in production, render actual map)
        dummy_png = base64.b64encode(b'fake_png_data').decode('utf-8')
        
        if output_format == 'html':
            html_overlay = '<html><body><h1>Air Quality for {}</h1><p>Avg AQI: {}</p></body></html>'.format(region, aqi_data['avg_aqi'])
            return json.dumps({'html': html_overlay, 'metadata': aqi_data}, ensure_ascii=False)
        else:
            return json.dumps({'image_base64': dummy_png, 'metadata': aqi_data}, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': 'Invalid JSON payload: ' + str(e)})
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "generate_air_quality_visualization",
    "description": "Generate an air quality index (AQI) visualization overlay on a geographic map for a given region and time range. Returns a base64-encoded PNG image showing pollutant levels (PM2.5, PM10, O3, NO2, SO2, CO) with color-coded AQI categories (Good, Moderate, Unhealthy for Sensitive Groups, Unhealthy, Very Unhealthy, Hazardous) and station markers, used for environmental reporting and public health advisories.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "region": {
            "type": "string",
            "description": "Geographic region name or bounding box coordinates (e.g., 'Beijing' or '39.9,116.4,40.0,116.5'). Supports city names and lat/lon comma-separated ranges."
        },
        "start_date": {
            "type": "string",
            "description": "Start date for data aggregation in ISO 8601 format (YYYY-MM-DD). Must be earlier than end_date."
        },
        "end_date": {
            "type": "string",
            "description": "End date for data aggregation (YYYY-MM-DD). Must be after start_date."
        },
        "pollutants": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "pm25",
                    "pm10",
                    "o3",
                    "no2",
                    "so2",
                    "co"
                ]
            },
            "description": "Optional: List of pollutants to include in the visualization. Default is all six if not provided."
        },
        "map_style": {
            "type": "string",
            "enum": [
                "satellite",
                "street",
                "light",
                "dark"
            ],
            "description": "Optional: Base map style for the visualization. Default is 'street'."
        },
        "output_format": {
            "type": "string",
            "enum": [
                "png_base64",
                "html"
            ],
            "description": "Optional: Output format. 'png_base64' returns a base64-encoded PNG string; 'html' returns an interactive HTML page. Default is 'png_base64'."
        }
    },
    "required": [
        "region",
        "start_date",
        "end_date"
    ]
},
}
