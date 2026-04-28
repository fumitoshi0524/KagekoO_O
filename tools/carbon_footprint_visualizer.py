"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a visual carbon footprint breakdown chart from user-reported activity data."""
    import json
    try:
        data = json.loads(payload)
        required = ['transport_km', 'electricity_kwh', 'diet_type', 'waste_kg']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required field: {field}'})
        transport_km = float(data['transport_km'])
        electricity_kwh = float(data['electricity_kwh'])
        diet_type = data['diet_type']
        waste_kg = float(data['waste_kg'])
        chart_format = data.get('chart_format', 'svg')
        
        # Emission factors (kg CO2e per unit)
        transport_factor = 0.24  # per km
        electricity_factor = 0.5  # per kWh
        diet_factors = {'vegan': 1.5, 'vegetarian': 2.0, 'mixed': 3.5, 'meat_heavy': 5.0}  # per day
        waste_factor = 0.6  # per kg
        
        # Monthly emissions
        transport_emissions = transport_km * transport_factor
        electricity_emissions = electricity_kwh * electricity_factor
        diet_emissions = diet_factors.get(diet_type, 3.5) * 30  # 30 days
        waste_emissions = waste_kg * waste_factor
        
        categories = {
            'transport': round(transport_emissions, 2),
            'electricity': round(electricity_emissions, 2),
            'diet': round(diet_emissions, 2),
            'waste': round(waste_emissions, 2)
        }
        total_emissions = round(sum(categories.values()), 2)
        
        if chart_format == 'json_data':
            result = {
                'total_emissions_kg_co2e': total_emissions,
                'categories': categories,
                'unit': 'kg CO2e per month'
            }
        else:
            # Generate SVG bar chart
            max_val = max(categories.values()) if categories.values() else 1
            bar_width = 120
            bar_gap = 20
            svg_width = 600
            svg_height = 400
            bars = []
            x = 50
            color_map = {'transport': '#4CAF50', 'electricity': '#FF9800', 'diet': '#F44336', 'waste': '#9C27B0'}
            for cat, val in categories.items():
                bar_height = (val / max_val) * 250 if max_val > 0 else 0
                y = svg_height - 60 - bar_height
                bars.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color_map[cat]}" rx="4" ry="4"/>')
                bars.append(f'<text x="{x + bar_width/2}" y="{svg_height - 40}" text-anchor="middle" font-family="Arial" font-size="14">{cat.capitalize()}</text>')
                bars.append(f'<text x="{x + bar_width/2}" y="{y - 10}" text-anchor="middle" font-family="Arial" font-size="12" fill="#333">{val} kg</text>')
                x += bar_width + bar_gap
            svg_content = f'''<svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
                <rect width="100%" height="100%" fill="#f9f9f9"/>
                <text x="{svg_width/2}" y="30" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold">Monthly Carbon Footprint</text>
                <text x="{svg_width/2}" y="55" text-anchor="middle" font-family="Arial" font-size="16" fill="#666">Total: {total_emissions} kg CO2e</text>
                {"".join(bars)}
            </svg>'''
            result = {'chart_data': svg_content, 'format': chart_format, 'total_emissions_kg_co2e': total_emissions}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "carbon_footprint_visualizer",
    "description": "Generate a visual carbon footprint breakdown chart from user-reported activity data, showing emission contributions by category (transport, energy, diet, waste) and total CO₂ equivalent, to help users understand their environmental impact.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "transport_km": {
            "type": "number",
            "description": "Monthly kilometers traveled by car (gasoline average).",
            "examples": [
                1200
            ]
        },
        "electricity_kwh": {
            "type": "number",
            "description": "Monthly household electricity consumption in kWh.",
            "examples": [
                350
            ]
        },
        "diet_type": {
            "type": "string",
            "description": "Dietary pattern for food-related emissions.",
            "enum": [
                "vegan",
                "vegetarian",
                "mixed",
                "meat_heavy"
            ]
        },
        "waste_kg": {
            "type": "number",
            "description": "Monthly household waste generated in kilograms.",
            "examples": [
                30
            ]
        },
        "chart_format": {
            "type": "string",
            "description": "Optional: desired output format for the visualization. Default is 'svg'.",
            "enum": [
                "svg",
                "png",
                "json_data"
            ],
            "default": "svg"
        }
    },
    "required": [
        "transport_km",
        "electricity_kwh",
        "diet_type",
        "waste_kg"
    ]
},
}
