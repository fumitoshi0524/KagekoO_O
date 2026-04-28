"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math

    try:
        data = json.loads(payload)
        items = data.get('wardrobe_items', [])
        temp = data.get('current_temperature_c')
        precip = data.get('precipitation_chance', 0)
        wind = data.get('wind_speed_kmh', 0)
        style = data.get('style_preference', 'any')

        if not items:
            return json.dumps({'error': 'Wardrobe is empty or not provided.'}, ensure_ascii=False)
        if temp is None:
            return json.dumps({'error': 'current_temperature_c is required.'}, ensure_ascii=False)

        # Calculate wind chill effect (simplified)
        if temp <= 10 and wind > 5:
            wind_chill = 13.12 + 0.6215 * temp - 11.37 * (wind ** 0.16) + 0.3965 * temp * (wind ** 0.16)
            effective_temp = min(temp, wind_chill)
        else:
            effective_temp = temp

        # Filter items by thermal range
        compatible = []
        for item in items:
            if item['min_temp_celsius'] <= effective_temp <= item['max_temp_celsius']:
                # If raining/snowing, prefer waterproof for outerwear or accessories
                if precip >= 50 and not item['is_waterproof'] and item['category'] in ('outerwear', 'footwear', 'accessory'):
                    continue
                # If style filter is active
                if style != 'any':
                    compatible.append(item)
                else:
                    compatible.append(item)

        if style != 'any':
            compatible = [item for item in compatible if item.get('preferred_style', 'any') == style]

        # Sort by how central the item is within its temperature range
        def score(item):
            mid = (item['min_temp_celsius'] + item['max_temp_celsius']) / 2
            return -abs(effective_temp - mid)

        compatible.sort(key=score, reverse=True)

        result = {
            'effective_temperature_c': round(effective_temp, 1),
            'wind_chill_applied': effective_temp != temp,
            'precipitation_risk': 'high' if precip >= 70 else 'moderate' if precip >= 30 else 'low',
            'compatible_items': compatible[:10],
            'total_compatible': len(compatible),
            'suggestion': f'Based on {round(effective_temp, 1)}°C effective temp, {int(precip)}% precipitation chance, and {int(wind)} km/h wind.'
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "wardrobe_weather_compatibility",
    "description": "Generate a visualization of clothing items from a user's virtual wardrobe that are suitable for the current or forecasted weather, based on temperature range, precipitation chance, and wind speed.",
    "category": "visualization",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "wardrobe_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Label of the clothing item (e.g., 'Cotton T-shirt', 'Wool Coat')."
                    },
                    "category": {
                        "type": "string",
                        "description": "Clothing category: top, bottom, outerwear, footwear, accessory.",
                        "enum": [
                            "top",
                            "bottom",
                            "outerwear",
                            "footwear",
                            "accessory"
                        ]
                    },
                    "material": {
                        "type": "string",
                        "description": "Material composition (e.g., cotton, wool, polyester, denim).",
                        "enum": [
                            "cotton",
                            "wool",
                            "polyester",
                            "denim",
                            "leather",
                            "silk",
                            "linen",
                            "nylon",
                            "fleece",
                            "other"
                        ]
                    },
                    "is_waterproof": {
                        "type": "boolean",
                        "description": "Whether the item offers water resistance or is waterproof."
                    },
                    "max_temp_celsius": {
                        "type": "number",
                        "description": "Maximum comfortable temperature in degrees Celsius for wearing this item (e.g., 25 for a T-shirt, 5 for a heavy parka). Must be between -20 and 50."
                    },
                    "min_temp_celsius": {
                        "type": "number",
                        "description": "Minimum comfortable temperature in degrees Celsius for wearing this item (e.g., 18 for a T-shirt, -15 for a heavy parka). Must be between -20 and 50."
                    }
                },
                "required": [
                    "name",
                    "category",
                    "material",
                    "is_waterproof",
                    "max_temp_celsius",
                    "min_temp_celsius"
                ]
            },
            "description": "List of clothing items in the user's wardrobe with thermal and weather compatibility specs."
        },
        "current_temperature_c": {
            "type": "number",
            "description": "Current or forecasted outdoor temperature in degrees Celsius. Must be between -20 and 50."
        },
        "precipitation_chance": {
            "type": "number",
            "description": "Probability of precipitation as a percentage (0-100).",
            "minimum": 0,
            "maximum": 100
        },
        "wind_speed_kmh": {
            "type": "number",
            "description": "Wind speed in kilometers per hour (0-200). Higher winds reduce effective temperature.",
            "minimum": 0,
            "maximum": 200
        },
        "style_preference": {
            "type": "string",
            "description": "Optional: Desired outfit style. Filters results to match a specific aesthetic.",
            "enum": [
                "casual",
                "formal",
                "sporty",
                "bohemian",
                "minimalist",
                "vintage",
                "punk",
                "any"
            ],
            "default": "any"
        }
    },
    "required": [
        "wardrobe_items",
        "current_temperature_c",
        "precipitation_chance",
        "wind_speed_kmh"
    ]
},
}
