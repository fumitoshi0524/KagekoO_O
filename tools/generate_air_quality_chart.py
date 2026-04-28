"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a line chart visualization showing air quality index (AQI) trends over time for a specified location."""
    import json
    import random
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        location = data.get('location')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        pollutant = data.get('pollutant', 'pm2.5')
        chart_type = data.get('chart_type', 'line')
        width = data.get('width', 800)
        height = data.get('height', 500)

        if not location or not start_date_str or not end_date_str:
            return json.dumps({'error': 'Missing required fields: location, start_date, end_date'})

        # Validate date format
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return json.dumps({'error': 'Invalid date format. Use YYYY-MM-DD.'})

        if end_date < start_date:
            return json.dumps({'error': 'end_date must be after start_date'})

        # Generate synthetic but realistic AQI data
        random.seed(hash(location + start_date_str + end_date_str))
        days = (end_date - start_date).days + 1
        if days > 365:
            return json.dumps({'error': 'Date range cannot exceed 365 days.'})

        data_points = []
        base_aqi = {'pm2.5': 50, 'pm10': 80, 'o3': 60, 'no2': 40, 'so2': 20, 'co': 10}
        noise_range = {'pm2.5': 30, 'pm10': 40, 'o3': 25, 'no2': 20, 'so2': 15, 'co': 8}

        for i in range(days):
            current_date = start_date + timedelta(days=i)
            base = base_aqi.get(pollutant, 50)
            noise = noise_range.get(pollutant, 20)
            # Add seasonal variation
            seasonal = 10 * (1 if pollutant in ['o3'] else -1) if current_date.month in [6,7,8] else 0
            value = max(0, base + random.randint(-noise, noise) + seasonal)
            data_points.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': round(value, 1),
                'unit': 'µg/m³' if pollutant != 'co' else 'ppm',
                'pollutant': pollutant
            })

        # Generate chart base64 (simplified placeholder - in real implementation would use matplotlib)
        # Here we return a data URI for a simple SVG chart
        chart_svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        chart_svg += f'<rect width="100%" height="100%" fill="#f0f8ff"/>'
        chart_svg += f'<text x="20" y="30" font-size="16" font-weight="bold">AQI Trend for {location}</text>'
        chart_svg += f'<text x="20" y="50" font-size="12">Pollutant: {pollutant.upper()} | {start_date_str} to {end_date_str}</text>'

        # Simple line drawing
        if len(data_points) > 1:
            margin = 60
            plot_width = width - 2 * margin
            plot_height = height - 2 * margin - 40
            values = [dp['value'] for dp in data_points]
            min_val = min(values)
            max_val = max(values)
            val_range = max(max_val - min_val, 1)

            points = []
            for idx, dp in enumerate(data_points):
                x = margin + (idx / (len(data_points) - 1)) * plot_width
                y = margin + 40 + (1 - (dp['value'] - min_val) / val_range) * plot_height
                points.append(f'{x},{y}')

            if chart_type == 'line':
                polyline = ' '.join(points)
                chart_svg += f'<polyline points="{polyline}" fill="none" stroke="#2b6cb0" stroke-width="2"/>'
            elif chart_type == 'area':
                polyline = ' '.join(points)
                bottom_points = f'{margin + plot_width},{margin + 40 + plot_height} {margin},{margin + 40 + plot_height}'
                chart_svg += f'<polygon points="{polyline} {bottom_points}" fill="#2b6cb0" fill-opacity="0.2" stroke="#2b6cb0" stroke-width="2"/>'
            elif chart_type == 'bar':
                bar_width = plot_width / len(data_points) * 0.8
                for idx, dp in enumerate(data_points):
                    x = margin + (idx / len(data_points)) * plot_width + (bar_width * 0.1)
                    y = margin + 40 + (1 - (dp['value'] - min_val) / val_range) * plot_height
                    bar_height = (dp['value'] - min_val) / val_range * plot_height
                    chart_svg += f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="#2b6cb0" opacity="0.7"/>'

            # Y-axis labels
            for i in range(5):
                val = min_val + (i / 4) * val_range
                y = margin + 40 + (1 - i / 4) * plot_height
                chart_svg += f'<text x="{margin - 10}" y="{y + 5}" font-size="10" text-anchor="end">{round(val, 1)}</text>'

        chart_svg += '</svg>'

        result = {
            'chart_svg': chart_svg,
            'metadata': {
                'location': location,
                'pollutant': pollutant,
                'chart_type': chart_type,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'data_points': len(data_points),
                'average_value': round(sum(dp['value'] for dp in data_points) / len(data_points), 1),
                'max_value': max(dp['value'] for dp in data_points),
                'min_value': min(dp['value'] for dp in data_points)
            }
        }

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "generate_air_quality_chart",
    "description": "Generate a line chart visualization showing air quality index (AQI) trends over time for a specified location, using daily pollutant data (PM2.5, PM10, O3, NO2, SO2, CO) to help environmental analysts monitor pollution patterns and assess compliance with air quality standards.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "Name of the city or monitoring station for which to generate the chart (e.g., 'Beijing', 'Los Angeles')."
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the time range in YYYY-MM-DD format."
        },
        "end_date": {
            "type": "string",
            "description": "End date for the time range in YYYY-MM-DD format."
        },
        "pollutant": {
            "type": "string",
            "description": "Optional: Pollutant to plot (default 'pm2.5'). Options: pm2.5, pm10, o3, no2, so2, co.",
            "enum": [
                "pm2.5",
                "pm10",
                "o3",
                "no2",
                "so2",
                "co"
            ],
            "default": "pm2.5"
        },
        "chart_type": {
            "type": "string",
            "description": "Optional: Type of chart to generate. Options: line, bar, area (default 'line').",
            "enum": [
                "line",
                "bar",
                "area"
            ],
            "default": "line"
        },
        "width": {
            "type": "integer",
            "description": "Optional: Width of the output chart image in pixels (default 800).",
            "default": 800,
            "minimum": 400,
            "maximum": 2000
        },
        "height": {
            "type": "integer",
            "description": "Optional: Height of the output chart image in pixels (default 500).",
            "default": 500,
            "minimum": 300,
            "maximum": 1500
        }
    },
    "required": [
        "location",
        "start_date",
        "end_date"
    ]
},
}
