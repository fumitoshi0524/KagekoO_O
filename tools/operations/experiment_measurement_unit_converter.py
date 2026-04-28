"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        value = data.get('value')
        from_unit = data.get('from_unit')
        to_unit = data.get('to_unit')
        if value is None or from_unit is None or to_unit is None:
            return json.dumps({'error': 'Missing required parameters: value, from_unit, to_unit'})
        
        # Conversion factors to SI base units
        length_map = {
            'm': 1.0, 'cm': 0.01, 'mm': 0.001, 'km': 1000.0,
            'in': 0.0254, 'ft': 0.3048, 'mile': 1609.344
        }
        mass_map = {
            'kg': 1.0, 'g': 0.001, 'mg': 1e-6, 'lb': 0.45359237, 'oz': 0.028349523125
        }
        volume_map = {
            'L': 1.0, 'mL': 0.001, 'gal': 3.785411784, 'qt': 0.946352946, 'cup': 0.2365882365
        }
        temp_convert = {
            'C': lambda x: x + 273.15,
            'F': lambda x: (x + 459.67) * 5/9,
            'K': lambda x: x
        }
        temp_invert = {
            'C': lambda x: x - 273.15,
            'F': lambda x: x*9/5 - 459.67,
            'K': lambda x: x
        }
        pressure_map = {
            'Pa': 1.0, 'kPa': 1000.0, 'atm': 101325.0, 'mmHg': 133.322, 'bar': 100000.0, 'psi': 6894.75729
        }
        concentration_map = {
            'mol/L': 1.0, 'mM': 0.001, 'µM': 1e-6
        }
        time_map = {
            's': 1.0, 'min': 60.0, 'h': 3600.0, 'day': 86400.0
        }
        
        # Infer category if not provided
        category = data.get('category')
        if category is None:
            if from_unit in length_map and to_unit in length_map:
                category = 'length'
            elif from_unit in mass_map and to_unit in mass_map:
                category = 'mass'
            elif from_unit in volume_map and to_unit in volume_map:
                category = 'volume'
            elif from_unit in temp_convert and to_unit in temp_convert:
                category = 'temperature'
            elif from_unit in pressure_map and to_unit in pressure_map:
                category = 'pressure'
            elif from_unit in concentration_map and to_unit in concentration_map:
                category = 'concentration'
            elif from_unit in time_map and to_unit in time_map:
                category = 'time'
            else:
                return json.dumps({'error': 'Could not infer category from units. Please specify category.', 'from_unit': from_unit, 'to_unit': to_unit})
        
        result = {}
        conversion_factor = None
        if category == 'temperature':
            if from_unit == to_unit:
                converted = value
                conversion_factor = 1.0
            else:
                kelvin = temp_convert[from_unit](value)
                converted = temp_invert[to_unit](kelvin)
                conversion_factor = (temp_invert[to_unit](temp_convert[from_unit](100.0) - 273.15) - temp_invert[to_unit](temp_convert[from_unit](0.0) - 273.15)) / 100.0
        else:
            if category == 'length':
                base_map = length_map
            elif category == 'mass':
                base_map = mass_map
            elif category == 'volume':
                base_map = volume_map
            elif category == 'pressure':
                base_map = pressure_map
            elif category == 'concentration':
                base_map = concentration_map
            elif category == 'time':
                base_map = time_map
            else:
                return json.dumps({'error': 'Unsupported category', 'category': category})
            
            if from_unit not in base_map or to_unit not in base_map:
                return json.dumps({'error': f'Units not found in {category} category', 'from_unit': from_unit, 'to_unit': to_unit})
            base_value = value * base_map[from_unit]
            converted = base_value / base_map[to_unit]
            conversion_factor = base_map[from_unit] / base_map[to_unit]
        
        result['original_value'] = value
        result['from_unit'] = from_unit
        result['converted_value'] = round(converted, 12)
        result['to_unit'] = to_unit
        result['category'] = category
        if conversion_factor is not None:
            result['conversion_factor'] = round(conversion_factor, 12)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})



TOOL_SPEC = {
    "name": "experiment_measurement_unit_converter",
    "description": "Convert scientific measurement units across SI, imperial, and specialized laboratory scales for variables such as length, mass, volume, temperature, pressure, concentration, and time, returning the converted value and the conversion factor used.",
    "category": "operations",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "value": {
            "type": "number",
            "description": "The numeric value to be converted."
        },
        "from_unit": {
            "type": "string",
            "description": "The unit of the input value. Supported units: m, cm, mm, km, in, ft, mile, kg, g, mg, lb, oz, L, mL, gal, qt, cup, C, F, K, Pa, kPa, atm, mmHg, bar, psi, mol/L, mM, µM, s, min, h, day.",
            "enum": [
                "m",
                "cm",
                "mm",
                "km",
                "in",
                "ft",
                "mile",
                "kg",
                "g",
                "mg",
                "lb",
                "oz",
                "L",
                "mL",
                "gal",
                "qt",
                "cup",
                "C",
                "F",
                "K",
                "Pa",
                "kPa",
                "atm",
                "mmHg",
                "bar",
                "psi",
                "mol/L",
                "mM",
                "µM",
                "s",
                "min",
                "h",
                "day"
            ]
        },
        "to_unit": {
            "type": "string",
            "description": "The target unit for conversion (same unit list as from_unit)."
        },
        "category": {
            "type": "string",
            "description": "Optional: Specify the measurement category to enforce consistent conversion (length, mass, volume, temperature, pressure, concentration, time). If omitted, the system infers from the units.",
            "enum": [
                "length",
                "mass",
                "volume",
                "temperature",
                "pressure",
                "concentration",
                "time"
            ]
        }
    },
    "required": [
        "value",
        "from_unit",
        "to_unit"
    ]
},
}
