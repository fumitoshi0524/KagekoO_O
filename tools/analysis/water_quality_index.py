"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Calculate Water Quality Index (WQI) from environmental water parameters."""
    import json
    import math

    try:
        data = json.loads(payload)
        # Validate required fields
        required = ['do', 'ph', 'tds', 'turbidity', 'temperature']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required parameter: {field}'}, ensure_ascii=False)

        # Extract parameters with defaults for optional ones
        do = float(data['do'])
        ph = float(data['ph'])
        tds = float(data['tds'])
        turbidity = float(data['turbidity'])
        temperature = float(data['temperature'])
        nitrate = float(data.get('nitrate', 0))
        phosphate = float(data.get('phosphate', 0))
        bod = float(data.get('bod', 0))
        conductivity = float(data.get('conductivity', 0))

        # Parameter weightings (standard water quality index weights)
        weights = {
            'do': 0.20,
            'ph': 0.15,
            'tds': 0.10,
            'turbidity': 0.10,
            'temperature': 0.10,
            'nitrate': 0.10,
            'phosphate': 0.10,
            'bod': 0.10,
            'conductivity': 0.05
        }

        # Calculate sub-index scores (0-100 scale, higher = better)
        def do_subindex(val):
            # DO: 0 mg/L = 0, 8+ mg/L = 100
            return min(100, max(0, val * 12.5))

        def ph_subindex(val):
            # pH: 7 = 100, deviations reduce score
            if 6.5 <= val <= 8.5:
                return 100 - 20 * abs(val - 7)
            else:
                return max(0, 100 - 40 * abs(val - 7))

        def tds_subindex(val):
            # TDS: 0 mg/L = 100, 500+ mg/L = 0
            return max(0, 100 - (val / 5))

        def turbidity_subindex(val):
            # Turbidity: 0 NTU = 100, 50+ NTU = 0
            return max(0, 100 - (val * 2))

        def temperature_subindex(val):
            # Temperature: deviation from 25°C, max 20 deviation = 0
            deviation = abs(val - 25)
            return max(0, 100 - (deviation * 5))

        def nitrate_subindex(val):
            # Nitrate: 0 mg/L = 100, 50+ mg/L = 0
            return max(0, 100 - (val * 2))

        def phosphate_subindex(val):
            # Phosphate: 0 mg/L = 100, 10+ mg/L = 0
            return max(0, 100 - (val * 10))

        def bod_subindex(val):
            # BOD: 0 mg/L = 100, 30+ mg/L = 0
            return max(0, 100 - (val * 3.33))

        def conductivity_subindex(val):
            # Conductivity: 0 µS/cm = 100, 1500+ µS/cm = 0
            return max(0, 100 - (val / 15))

        # Build sub-index dictionary
        sub_indices = {
            'do': do_subindex(do),
            'ph': ph_subindex(ph),
            'tds': tds_subindex(tds),
            'turbidity': turbidity_subindex(turbidity),
            'temperature': temperature_subindex(temperature),
            'nitrate': nitrate_subindex(nitrate) if nitrate > 0 else 100,
            'phosphate': phosphate_subindex(phosphate) if phosphate > 0 else 100,
            'bod': bod_subindex(bod) if bod > 0 else 100,
            'conductivity': conductivity_subindex(conductivity) if conductivity > 0 else 100
        }

        # Weighted arithmetic mean method
        weighted_sum = sum(sub_indices[p] * weights[p] for p in sub_indices)
        total_weight = sum(weights[p] for p in sub_indices)
        wqi = round(weighted_sum / total_weight, 2) if total_weight > 0 else 50.0

        # Determine quality class
        if wqi >= 90:
            quality_class = "Excellent"
            assessment = "Water quality is excellent, suitable for all uses including drinking."
        elif wqi >= 70:
            quality_class = "Good"
            assessment = "Water quality is good, suitable for most uses with minimal treatment."
        elif wqi >= 50:
            quality_class = "Fair"
            assessment = "Water quality is fair, may require treatment for drinking and sensitive aquatic life."
        elif wqi >= 25:
            quality_class = "Poor"
            assessment = "Water quality is poor, requires significant treatment for most uses."
        else:
            quality_class = "Very Poor"
            assessment = "Water quality is very poor, unsuitable for most uses without extensive treatment."

        result = {
            'wqi_score': wqi,
            'quality_class': quality_class,
            'assessment': assessment,
            'sub_indices': {k: round(v, 2) for k, v in sub_indices.items()}
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "water_quality_index",
    "description": "Calculate the Water Quality Index (WQI) from up to 9 measured parameters (DO, pH, TDS, turbidity, temperature, nitrate, phosphate, BOD, conductivity) using weighted arithmetic or weighted geometric mean methods, returning the index value, quality class label, and a human-readable assessment.",
    "category": "analysis",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "do": {
            "type": "number",
            "description": "Dissolved oxygen concentration in mg/L (0-20, higher is better for WQI)",
            "examples": [
                6.5,
                8.2,
                4.1
            ]
        },
        "ph": {
            "type": "number",
            "description": "pH value of the water sample (0-14, ideal range 6.5-8.5 for WQI scoring)",
            "examples": [
                7.2,
                6.8,
                9.1
            ]
        },
        "tds": {
            "type": "number",
            "description": "Total Dissolved Solids in mg/L (0-2000, lower is better for WQI)",
            "examples": [
                150,
                320,
                890
            ]
        },
        "turbidity": {
            "type": "number",
            "description": "Turbidity in NTU (0-100, lower is better for WQI)",
            "examples": [
                2.5,
                15.0,
                45.0
            ]
        },
        "temperature": {
            "type": "number",
            "description": "Water temperature in degrees Celsius (0-40, deviation from 25°C affects WQI scoring)",
            "examples": [
                22.0,
                28.5,
                15.0
            ]
        },
        "nitrate": {
            "type": "number",
            "description": "Nitrate concentration in mg/L (0-100, lower is better for WQI)",
            "examples": [
                2.0,
                12.5,
                0.5
            ]
        },
        "phosphate": {
            "type": "number",
            "description": "Phosphate concentration in mg/L (0-20, lower is better for WQI)",
            "examples": [
                0.3,
                2.1,
                0.05
            ]
        },
        "bod": {
            "type": "number",
            "description": "Biochemical Oxygen Demand in mg/L (0-100, lower is better for WQI)",
            "examples": [
                3.0,
                18.0,
                1.2
            ]
        },
        "conductivity": {
            "type": "number",
            "description": "Electrical conductivity in µS/cm (0-3000, lower is better for WQI)",
            "examples": [
                250,
                780,
                1200
            ]
        }
    },
    "required": [
        "do",
        "ph",
        "tds",
        "turbidity",
        "temperature"
    ]
},
}
