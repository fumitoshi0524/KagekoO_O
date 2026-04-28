"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a treemap visualization of greenhouse gas emissions broken down by sector and subsector for a given region and year."""
    import json
    try:
        data = json.loads(payload)
        region = data.get("region")
        year = data.get("year")
        scope = data.get("scope", "all")
        normalize = data.get("normalize", False)
        
        if not region or not year:
            return json.dumps({"error": "region and year are required"}, ensure_ascii=False)
        if not isinstance(region, str) or len(region) < 1:
            return json.dumps({"error": "region must be a non-empty string"}, ensure_ascii=False)
        if not isinstance(year, int) or year < 1990 or year > 2023:
            return json.dumps({"error": "year must be an integer between 1990 and 2023"}, ensure_ascii=False)
        if scope not in ["all", "energy", "agriculture", "industrial", "waste", "land_use"]:
            return json.dumps({"error": "invalid scope, must be one of: all, energy, agriculture, industrial, waste, land_use"}, ensure_ascii=False)
        
        # Simulated emissions database with realistic values
        emissions_db = {
            "US": {
                2020: {
                    "Energy": {"Electricity Generation": 2500, "Transportation": 1800, "Fugitive Emissions": 340},
                    "Agriculture": {"Livestock": 620, "Crop Production": 310, "Fertilizer Use": 280},
                    "Industrial": {"Cement Production": 410, "Chemical Manufacturing": 290, "Metal Smelting": 180},
                    "Waste": {"Landfills": 420, "Wastewater": 190, "Incineration": 80},
                    "Land Use": {"Deforestation": -150, "Afforestation": 90, "Soil Management": 120}
                },
                2021: {
                    "Energy": {"Electricity Generation": 2450, "Transportation": 1850, "Fugitive Emissions": 330},
                    "Agriculture": {"Livestock": 630, "Crop Production": 305, "Fertilizer Use": 275},
                    "Industrial": {"Cement Production": 420, "Chemical Manufacturing": 295, "Metal Smelting": 175},
                    "Waste": {"Landfills": 415, "Wastewater": 195, "Incineration": 85},
                    "Land Use": {"Deforestation": -140, "Afforestation": 95, "Soil Management": 115}
                }
            },
            "CN": {
                2020: {
                    "Energy": {"Coal Power": 5800, "Transportation": 2100, "Industrial Energy": 1900},
                    "Agriculture": {"Rice Cultivation": 450, "Livestock": 380, "Fertilizer": 320},
                    "Industrial": {"Cement": 1200, "Steel": 950, "Chemicals": 600},
                    "Waste": {"Landfills": 320, "Wastewater": 150, "Incineration": 120},
                    "Land Use": {"Deforestation": 500, "Afforestation": -200, "Soil": 180}
                }
            },
            "EU": {
                2020: {
                    "Energy": {"Electricity": 1500, "Transport": 1100, "Buildings": 600},
                    "Agriculture": {"Livestock": 420, "Crops": 250, "Fertilizer": 180},
                    "Industrial": {"Manufacturing": 350, "Chemicals": 200, "Mining": 90},
                    "Waste": {"Landfills": 200, "Wastewater": 120, "Recycling": -50},
                    "Land Use": {"Forestry": 100, "Agriculture Soils": 80, "Peatlands": 60}
                }
            },
            "global": {
                2020: {
                    "Energy": {"Power Generation": 15500, "Transport": 7800, "Buildings": 3200, "Other Energy": 1400},
                    "Agriculture": {"Livestock": 5200, "Crops": 2800, "Fertilizer": 1800, "Rice": 1500},
                    "Industrial": {"Cement": 2500, "Steel": 2200, "Chemicals": 1800, "Mining": 600},
                    "Waste": {"Landfills": 1800, "Wastewater": 800, "Incineration": 400},
                    "Land Use": {"Deforestation": 4500, "Afforestation": -800, "Peat": 600, "Soil": 400}
                }
            }
        }
        
        if region not in emissions_db:
            # Generate synthetic data for unrecognized regions
            return json.dumps({"error": f"No data available for region '{region}'. Available regions: {list(emissions_db.keys())}"}, ensure_ascii=False)
        if year not in emissions_db[region]:
            available_years = list(emissions_db[region].keys())
            return json.dumps({"error": f"No data available for year {year}. Available years: {available_years}"}, ensure_ascii=False)
        
        # Apply scope filter
        raw_data = emissions_db[region][year]
        if scope != "all":
            scope_map = {
                "energy": "Energy",
                "agriculture": "Agriculture",
                "industrial": "Industrial",
                "waste": "Waste",
                "land_use": "Land Use"
            }
            sector_name = scope_map.get(scope)
            if sector_name and sector_name in raw_data:
                raw_data = {sector_name: raw_data[sector_name]}
            else:
                return json.dumps({"error": f"No data for scope '{scope}' in {region} {year}"}, ensure_ascii=False)
        
        # Build hierarchical treemap structure
        result = {
            "chart_type": "treemap",
            "title": f"Greenhouse Gas Emissions for {region} - {year}",
            "region": region,
            "year": year,
            "unit": "metric_tons_co2_equivalent",
            "total_emissions": 0,
            "hierarchy": []
        }
        
        total = 0
        hierarchy = []
        for sector, subsectors in raw_data.items():
            sector_total = sum(subsectors.values())
            total += sector_total
            children = [
                {"name": sub, "value": val, "sector": sector}
                for sub, val in subsectors.items()
            ]
            hierarchy.append({
                "name": sector,
                "value": sector_total,
                "children": children
            })
        
        result["total_emissions"] = total
        result["hierarchy"] = hierarchy
        
        if normalize and total > 0:
            def normalize_node(node):
                node["value"] = round(node["value"] / total * 100, 2)
                if "children" in node:
                    for child in node["children"]:
                        child["value"] = round(child["value"] / total * 100, 2)
                return node
            
            result["hierarchy"] = [normalize_node(n) for n in hierarchy]
            result["unit"] = "percentage"
        
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Processing error: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "emissions_treemap",
    "description": "Generate a treemap visualization of greenhouse gas emissions broken down by sector and subsector for a given region and year, returning hierarchical data with emission values in metric tons of CO2 equivalent for dashboard integration.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "region": {
            "type": "string",
            "description": "Geographic region or country code (ISO 3166-1 alpha-2) for the emissions data",
            "examples": [
                "US",
                "EU",
                "CN",
                "global"
            ]
        },
        "year": {
            "type": "integer",
            "description": "Calendar year for which emissions data is requested, must be between 1990 and 2023",
            "examples": [
                2020,
                2021,
                2022
            ]
        },
        "scope": {
            "type": "string",
            "description": "Optional: Emission scope filter - 'all' includes all sectors, 'energy' limits to energy-related emissions, 'agriculture' limits to agricultural emissions, 'industrial' limits to industrial processes",
            "enum": [
                "all",
                "energy",
                "agriculture",
                "industrial",
                "waste",
                "land_use"
            ],
            "default": "all"
        },
        "normalize": {
            "type": "boolean",
            "description": "Optional: If true, returns percentages instead of absolute values for relative comparison across regions",
            "default": false
        }
    },
    "required": [
        "region",
        "year"
    ]
},
}
