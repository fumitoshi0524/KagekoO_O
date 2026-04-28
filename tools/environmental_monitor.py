"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        location = data.get('location')
        temp = data.get('temperature_celsius')
        humidity = data.get('humidity_percent')
        aqi = data.get('aqi')
        co2 = data.get('co2_ppm')
        # Validate required fields
        if not all([location, temp is not None, humidity is not None, aqi is not None, co2 is not None]):
            return json.dumps({'error': 'Missing required fields'})
        # Validate ranges
        if not (-50 <= temp <= 60):
            return json.dumps({'error': 'Temperature out of range (-50 to 60 C)'})
        if not (0 <= humidity <= 100):
            return json.dumps({'error': 'Humidity out of range (0-100%)'})
        if not (0 <= aqi <= 500):
            return json.dumps({'error': 'AQI out of range (0-500)'})
        if not (300 <= co2 <= 5000):
            return json.dumps({'error': 'CO2 out of range (300-5000 ppm)'})
        # Compute health scores and alerts
        threshold_temp_high = data.get('optional_threshold_temperature_high', 40.0)
        threshold_aqi_high = data.get('optional_threshold_aqi_high', 200)
        alerts = []
        if temp > threshold_temp_high:
            alerts.append(f'High temperature alert: {temp}C exceeds {threshold_temp_high}C')
        if aqi > threshold_aqi_high:
            alerts.append(f'High AQI alert: {aqi} exceeds {threshold_aqi_high}')
        if co2 > 1000:
            alerts.append(f'CO2 level {co2} ppm above 1000 - ventilation recommended')
        # Compute composite environmental score (0-100, higher is better)
        # Simple heuristic: penalize extremes
        temp_score = max(0, 100 - abs(temp - 22) * 2)  # 22C ideal
        humidity_score = max(0, 100 - abs(humidity - 50) * 2)  # 50% ideal
        aqi_score = max(0, 100 - (aqi / 5))  # lower AQI better
        co2_score = max(0, 100 - max(0, (co2 - 400) / 10))  # under 400 ideal
        overall_score = round((temp_score + humidity_score + aqi_score + co2_score) / 4, 1)
        result = {
            'location': location,
            'timestamp': None,
            'metrics': {
                'temperature_celsius': temp,
                'humidity_percent': humidity,
                'aqi': aqi,
                'co2_ppm': co2
            },
            'environmental_score': overall_score,
            'alerts': alerts if alerts else ['No alerts']
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "environmental_monitor",
    "description": "Collect and report environmental health metrics from a local or remote sensor node, including temperature, humidity, air quality index (AQI), and CO2 levels, returning a structured summary for sustainability monitoring and alerting.",
    "category": "system",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "Geographic identifier for the sensor node, e.g., 'Building A - Rooftop' or 'Park Sensor 3'. Accepts any non-empty string."
        },
        "temperature_celsius": {
            "type": "number",
            "description": "Current ambient temperature in degrees Celsius, range -50 to 60."
        },
        "humidity_percent": {
            "type": "number",
            "description": "Relative humidity as a percentage, range 0 to 100."
        },
        "aqi": {
            "type": "integer",
            "description": "Air Quality Index (AQI) value, 0 to 500. Lower is better. Values above 100 indicate unhealthy conditions."
        },
        "co2_ppm": {
            "type": "integer",
            "description": "Carbon dioxide concentration in parts per million (ppm), range 300 to 5000. Outdoor baseline ~400 ppm."
        },
        "optional_threshold_temperature_high": {
            "type": "number",
            "description": "Optional: high temperature threshold in Celsius for alert generation (e.g., 35.0). If omitted, default is 40.0."
        },
        "optional_threshold_aqi_high": {
            "type": "integer",
            "description": "Optional: high AQI threshold for alert generation (e.g., 150). If omitted, default is 200."
        }
    },
    "required": [
        "location",
        "temperature_celsius",
        "humidity_percent",
        "aqi",
        "co2_ppm"
    ]
},
}
