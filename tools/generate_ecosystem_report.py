"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generates a comprehensive ecosystem health report for a specified geographic region."""
    import json
    import math
    import random
    from datetime import datetime

    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ["region_name", "latitude", "longitude", "assessment_type"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)
        
        region = data["region_name"]
        lat = float(data["latitude"])
        lon = float(data["longitude"])
        assessment = data["assessment_type"]
        radius = data.get("radius_km", 50)
        include_recs = data.get("include_recommendations", True)
        
        # Validate ranges
        if lat < -90 or lat > 90:
            return json.dumps({"error": "Latitude must be between -90 and 90"}, ensure_ascii=False)
        if lon < -180 or lon > 180:
            return json.dumps({"error": "Longitude must be between -180 and 180"}, ensure_ascii=False)
        if radius < 1 or radius > 500:
            return json.dumps({"error": "radius_km must be between 1 and 500"}, ensure_ascii=False)
        if assessment not in ["biodiversity", "water_quality", "vegetation_health", "climate_impact", "comprehensive"]:
            return json.dumps({"error": "Invalid assessment_type"}, ensure_ascii=False)
        
        # Simulate ecosystem data based on latitude (proxy for climate zones)
        lat_abs = abs(lat)
        if lat_abs < 23.5:
            climate_zone = "tropical"
            temp_range = (25, 35)
            rainfall_mm = random.randint(1500, 3000)
        elif lat_abs < 45:
            climate_zone = "temperate"
            temp_range = (5, 25)
            rainfall_mm = random.randint(500, 1500)
        elif lat_abs < 66.5:
            climate_zone = "continental"
            temp_range = (-10, 15)
            rainfall_mm = random.randint(300, 800)
        else:
            climate_zone = "polar"
            temp_range = (-30, 0)
            rainfall_mm = random.randint(100, 400)
        
        avg_temp = round(random.uniform(*temp_range), 1)
        area_km2 = round(math.pi * radius ** 2, 2)
        
        # Generate simulated metrics
        biodiversity_index = round(random.uniform(0.3, 0.95), 2)
        species_count = int(biodiversity_index * 1000 + random.randint(50, 200))
        vegetation_cover_pct = round(random.uniform(40, 98), 1)
        water_quality_score = round(random.uniform(0.4, 0.9), 2)
        carbon_sequestration_tons = round(random.uniform(10000, 50000) * (radius / 50), 0)
        
        # Compute health score based on selected assessment
        if assessment == "biodiversity":
            health_score = round(biodiversity_index * 100, 1)
        elif assessment == "water_quality":
            health_score = round(water_quality_score * 100, 1)
        elif assessment == "vegetation_health":
            health_score = round(vegetation_cover_pct, 1)
        elif assessment == "climate_impact":
            health_score = round(100 - (avg_temp * 2 + (100 - rainfall_mm / 30)), 1)
        else:  # comprehensive
            health_score = round((biodiversity_index + water_quality_score + (vegetation_cover_pct / 100)) / 3 * 100, 1)
        
        health_score = max(0, min(100, health_score))
        
        # Determine health level
        if health_score >= 80:
            health_level = "Excellent"
        elif health_score >= 60:
            health_level = "Good"
        elif health_score >= 40:
            health_level = "Fair"
        elif health_score >= 20:
            health_level = "Poor"
        else:
            health_level = "Critical"
        
        # Generate recommendations if requested
        recommendations = []
        if include_recs:
            if biodiversity_index < 0.6:
                recommendations.append("Establish wildlife corridors to connect fragmented habitats")
            if vegetation_cover_pct < 60:
                recommendations.append("Implement reforestation programs with native species")
            if water_quality_score < 0.7:
                recommendations.append("Reduce agricultural runoff through buffer zones and sustainable farming practices")
            if avg_temp > 20 and climate_zone != "tropical":
                recommendations.append("Monitor temperature anomalies for early signs of climate stress")
            if health_score < 50:
                recommendations.append("Conduct detailed ecological survey to identify specific threats")
            recommendations.append("Engage local communities in conservation and monitoring programs")
        
        result = {
            "report_id": f"ECO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000,9999)}",
            "generated_at": datetime.now().isoformat(),
            "region": region,
            "coordinates": {"latitude": lat, "longitude": lon},
            "assessed_area_km2": area_km2,
            "assessment_type": assessment,
            "climate_zone": climate_zone,
            "average_temperature_c": avg_temp,
            "annual_rainfall_mm": rainfall_mm,
            "ecosystem_metrics": {
                "biodiversity_index": biodiversity_index,
                "estimated_species_count": species_count,
                "vegetation_cover_percent": vegetation_cover_pct,
                "water_quality_score": water_quality_score,
                "carbon_sequestration_tons_per_year": int(carbon_sequestration_tons)
            },
            "health_score": health_score,
            "health_level": health_level
        }
        
        if include_recs and recommendations:
            result["recommendations"] = recommendations
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_ecosystem_report",
    "description": "Generates a comprehensive ecosystem health report for a specified geographic region by analyzing biodiversity indicators, vegetation coverage, water quality metrics, and climate patterns to produce a sustainability score and actionable conservation recommendations.",
    "category": "generate",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "region_name": {
            "type": "string",
            "description": "Name of the geographic region or ecosystem area (e.g., Amazon Rainforest, Great Barrier Reef)"
        },
        "latitude": {
            "type": "number",
            "description": "Latitude coordinate of the region center point in decimal degrees (range -90 to 90)"
        },
        "longitude": {
            "type": "number",
            "description": "Longitude coordinate of the region center point in decimal degrees (range -180 to 180)"
        },
        "assessment_type": {
            "type": "string",
            "enum": [
                "biodiversity",
                "water_quality",
                "vegetation_health",
                "climate_impact",
                "comprehensive"
            ],
            "description": "Type of ecosystem assessment to perform. Comprehensive includes all factors; others focus on specific areas."
        },
        "radius_km": {
            "type": "number",
            "description": "Optional: Radius in kilometers from the center point to define the assessment area (default 50 km, min 1, max 500). Must be positive.",
            "minimum": 1,
            "maximum": 500
        },
        "include_recommendations": {
            "type": "boolean",
            "description": "Optional: Whether to include actionable conservation recommendations in the report (default true)."
        }
    },
    "required": [
        "region_name",
        "latitude",
        "longitude",
        "assessment_type"
    ]
},
}
