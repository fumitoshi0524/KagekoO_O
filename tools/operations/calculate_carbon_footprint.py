"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        if 'electricity_kwh' not in data:
            return json.dumps({'error': 'Missing required parameter: electricity_kwh'}, ensure_ascii=False)
        
        # Emission factors (kg CO2e per unit) from EPA and DEFRA industry standards
        factors = {
            'electricity': 0.85,        # kg CO2e per kWh
            'natural_gas': 5.3,         # kg CO2e per therm
            'diesel': 2.68,             # kg CO2e per liter
            'gasoline': 2.31,           # kg CO2e per liter
            'air_economy': 0.15,        # kg CO2e per km
            'air_business': 0.30,       # kg CO2e per km
            'air_first': 0.45,          # kg CO2e per km
            'waste_landfill': 0.56      # kg CO2e per kg
        }
        
        total = 0.0
        breakdown = {}
        
        # Electricity
        elec_emissions = data['electricity_kwh'] * factors['electricity']
        total += elec_emissions
        breakdown['electricity'] = round(elec_emissions, 2)
        
        # Natural gas (optional)
        if 'natural_gas_therms' in data and data['natural_gas_therms'] > 0:
            gas_emissions = data['natural_gas_therms'] * factors['natural_gas']
            total += gas_emissions
            breakdown['natural_gas'] = round(gas_emissions, 2)
        
        # Diesel (optional)
        if 'diesel_liters' in data and data['diesel_liters'] > 0:
            diesel_emissions = data['diesel_liters'] * factors['diesel']
            total += diesel_emissions
            breakdown['diesel'] = round(diesel_emissions, 2)
        
        # Gasoline (optional)
        if 'gasoline_liters' in data and data['gasoline_liters'] > 0:
            gas_emissions = data['gasoline_liters'] * factors['gasoline']
            total += gas_emissions
            breakdown['gasoline'] = round(gas_emissions, 2)
        
        # Air travel (optional)
        if 'air_travel_km' in data and data['air_travel_km'] > 0:
            flight_class = data.get('flights_class', 'economy')
            factor_key = f'air_{flight_class}'
            if factor_key not in factors:
                factor_key = 'air_economy'
            air_emissions = data['air_travel_km'] * factors[factor_key]
            total += air_emissions
            breakdown['air_travel'] = round(air_emissions, 2)
        
        # Waste (optional)
        if 'waste_kg' in data and data['waste_kg'] > 0:
            waste_emissions = data['waste_kg'] * factors['waste_landfill']
            total += waste_emissions
            breakdown['waste'] = round(waste_emissions, 2)
        
        result = {
            'total_carbon_footprint_kg_co2e': round(total, 2),
            'total_carbon_footprint_tons_co2e': round(total / 1000, 4),
            'breakdown': breakdown,
            'unit': 'kg CO2 equivalent',
            'methodology': 'Based on EPA and DEFRA emission factors'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "calculate_carbon_footprint",
    "description": "Calculate the total carbon footprint in kg CO2 equivalent for a given business activity or supply chain operation, using industry-standard emission factors for electricity consumption, fuel usage, air travel, and waste generation.",
    "category": "operations",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "electricity_kwh": {
            "type": "number",
            "description": "Amount of electricity consumed in kilowatt-hours (kWh) for the reporting period.",
            "minimum": 0
        },
        "natural_gas_therms": {
            "type": "number",
            "description": "Optional: Amount of natural gas consumed in therms for heating or processes.",
            "minimum": 0
        },
        "diesel_liters": {
            "type": "number",
            "description": "Optional: Volume of diesel fuel used by vehicles or generators in liters.",
            "minimum": 0
        },
        "gasoline_liters": {
            "type": "number",
            "description": "Optional: Volume of gasoline fuel used by vehicles in liters.",
            "minimum": 0
        },
        "air_travel_km": {
            "type": "number",
            "description": "Optional: Total distance flown by business air travel in kilometers.",
            "minimum": 0
        },
        "flights_class": {
            "type": "string",
            "enum": [
                "economy",
                "business",
                "first"
            ],
            "description": "Optional: Class of air travel — affects emission factor (economy has lowest per-km emissions, first class highest). Defaults to economy.",
            "default": "economy"
        },
        "waste_kg": {
            "type": "number",
            "description": "Optional: Total waste generated in kilograms sent to landfill.",
            "minimum": 0
        }
    },
    "required": [
        "electricity_kwh"
    ]
},
}
