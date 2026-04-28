"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search and retrieve emission source records from an environmental database."""
    import json
    import math
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        if 'sector' not in data:
            raise ValueError("'sector' is required")
        if 'pollutant' not in data:
            raise ValueError("'pollutant' is required")
        
        sector = data['sector']
        pollutant = data['pollutant']
        region = data.get('region', None)
        compliance_status = data.get('compliance_status', 'all')
        min_emission = data.get('min_emission', None)
        max_emission = data.get('max_emission', None)
        year = data.get('year', 2023)
        page = data.get('page', 1)
        page_size = min(data.get('page_size', 20), 100)
        
        # Mock database of emission sources (in production, this would query a real database)
        mock_emission_sources = [
            {
                "facility_id": "FAC-001",
                "facility_name": "Green Valley Power Plant",
                "sector": "energy",
                "location": {"region": "Europe", "country": "Germany", "coordinates": {"lat": 51.1657, "lon": 10.4515}},
                "pollutants": {
                    "CO2": {"annual_emission_metric_tons": 2500000, "limit": 2800000, "unit": "metric_tons"},
                    "SO2": {"annual_emission_metric_tons": 4500, "limit": 5000, "unit": "metric_tons"},
                    "NOx": {"annual_emission_metric_tons": 3200, "limit": 3500, "unit": "metric_tons"}
                },
                "compliance_status": "compliant",
                "permit_number": "EU-2022-0458",
                "reporting_year": 2023
            },
            {
                "facility_id": "FAC-002",
                "facility_name": "Northern Steel Mill",
                "sector": "manufacturing",
                "location": {"region": "Europe", "country": "Sweden", "coordinates": {"lat": 59.3293, "lon": 18.0686}},
                "pollutants": {
                    "CO2": {"annual_emission_metric_tons": 1800000, "limit": 1500000, "unit": "metric_tons"},
                    "PM2.5": {"annual_emission_metric_tons": 850, "limit": 600, "unit": "metric_tons"},
                    "VOC": {"annual_emission_metric_tons": 220, "limit": 200, "unit": "metric_tons"}
                },
                "compliance_status": "non_compliant",
                "permit_number": "SE-2021-1122",
                "reporting_year": 2023
            },
            {
                "facility_id": "FAC-003",
                "facility_name": "Sunrise Solar Farm",
                "sector": "energy",
                "location": {"region": "North America", "country": "United States", "coordinates": {"lat": 34.0522, "lon": -118.2437}},
                "pollutants": {
                    "CO2": {"annual_emission_metric_tons": 50, "limit": 100, "unit": "metric_tons"}
                },
                "compliance_status": "compliant",
                "permit_number": "US-2020-9901",
                "reporting_year": 2023
            },
            {
                "facility_id": "FAC-004",
                "facility_name": "Delta Chemical Plant",
                "sector": "manufacturing",
                "location": {"region": "Asia", "country": "China", "coordinates": {"lat": 31.2304, "lon": 121.4737}},
                "pollutants": {
                    "VOC": {"annual_emission_metric_tons": 1200, "limit": 1000, "unit": "metric_tons"},
                    "ammonia": {"annual_emission_metric_tons": 340, "limit": 300, "unit": "metric_tons"},
                    "HFCs": {"annual_emission_metric_tons": 12, "limit": 10, "unit": "metric_tons"}
                },
                "compliance_status": "non_compliant",
                "permit_number": "CN-2022-3344",
                "reporting_year": 2023
            },
            {
                "facility_id": "FAC-005",
                "facility_name": "Pampas Agricultural Co-op",
                "sector": "agriculture",
                "location": {"region": "South America", "country": "Brazil", "coordinates": {"lat": -23.5505, "lon": -46.6333}},
                "pollutants": {
                    "methane": {"annual_emission_metric_tons": 85000, "limit": 90000, "unit": "metric_tons"},
                    "ammonia": {"annual_emission_metric_tons": 12000, "limit": 15000, "unit": "metric_tons"}
                },
                "compliance_status": "compliant",
                "permit_number": "BR-2023-7788",
                "reporting_year": 2023
            }
        ]
        
        # Filter results based on query parameters
        filtered_sources = []
        for source in mock_emission_sources:
            # Filter by sector
            if source['sector'] != sector:
                continue
            
            # Filter by pollutant (check if source emits the requested pollutant)
            if pollutant not in source['pollutants']:
                continue
            
            # Filter by region
            if region and region.lower() not in source['location']['region'].lower():
                continue
            
            # Filter by compliance status
            if compliance_status != 'all' and source['compliance_status'] != compliance_status:
                continue
            
            # Filter by emission quantity range
            emission_data = source['pollutants'][pollutant]
            emission_amount = emission_data['annual_emission_metric_tons']
            if min_emission is not None and emission_amount < min_emission:
                continue
            if max_emission is not None and emission_amount > max_emission:
                continue
            
            # Filter by year
            if source['reporting_year'] != year:
                continue
            
            filtered_sources.append(source)
        
        # Pagination
        total_results = len(filtered_sources)
        total_pages = max(1, math.ceil(total_results / page_size))
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_results)
        paginated_sources = filtered_sources[start_idx:end_idx]
        
        # Build result with relevant fields
        results = []
        for source in paginated_sources:
            emission_data = source['pollutants'][pollutant]
            results.append({
                'facility_id': source['facility_id'],
                'facility_name': source['facility_name'],
                'sector': source['sector'],
                'region': source['location']['region'],
                'country': source['location']['country'],
                'coordinates': source['location']['coordinates'],
                'pollutant': pollutant,
                'annual_emission_metric_tons': emission_data['annual_emission_metric_tons'],
                'regulatory_limit_metric_tons': emission_data['limit'],
                'compliance_status': source['compliance_status'],
                'permit_number': source['permit_number'],
                'reporting_year': source['reporting_year']
            })
        
        # Sort by emission amount descending
        results.sort(key=lambda x: x['annual_emission_metric_tons'], reverse=True)
        
        # Calculate summary statistics
        total_emission = sum(r['annual_emission_metric_tons'] for r in results)
        avg_emission = round(total_emission / len(results), 2) if results else 0
        max_emission_val = max(r['annual_emission_metric_tons'] for r in results) if results else 0
        min_emission_val = min(r['annual_emission_metric_tons'] for r in results) if results else 0
        
        result = {
            'success': True,
            'query': {
                'sector': sector,
                'pollutant': pollutant,
                'region': region,
                'year': year,
                'compliance_status': compliance_status
            },
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_results': total_results,
                'total_pages': total_pages
            },
            'summary': {
                'total_emission_metric_tons': total_emission,
                'average_emission_metric_tons': avg_emission,
                'max_emission_metric_tons': max_emission_val,
                'min_emission_metric_tons': min_emission_val,
                'facility_count': len(results)
            },
            'results': results
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except ValueError as ve:
        return json.dumps({'success': False, 'error': str(ve)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'success': False, 'error': f'An unexpected error occurred: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "emission_source_query",
    "description": "Search and retrieve emission source records from an environmental database by industry sector, pollutant type, geographic region, or compliance status. Returns detailed facility-level emission data including annual pollutant quantities, regulatory limits, and permit information for environmental impact analysis and regulatory compliance monitoring.",
    "category": "search",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "sector": {
            "type": "string",
            "description": "Industry sector to filter emission sources (e.g., manufacturing, energy, agriculture, transportation)",
            "enum": [
                "manufacturing",
                "energy",
                "agriculture",
                "transportation",
                "waste_management",
                "construction",
                "mining"
            ]
        },
        "pollutant": {
            "type": "string",
            "description": "Pollutant type to search for (e.g., CO2, SO2, NOx, PM2.5, VOC, methane, ammonia)",
            "enum": [
                "CO2",
                "SO2",
                "NOx",
                "PM2.5",
                "PM10",
                "VOC",
                "methane",
                "ammonia",
                "CFCs",
                "HFCs",
                "black_carbon",
                "mercury",
                "lead"
            ]
        },
        "region": {
            "type": "string",
            "description": "Geographic region or country name to constrain the search (e.g., Europe, North America, China, India, Global)"
        },
        "compliance_status": {
            "type": "string",
            "description": "Filter by regulatory compliance status of the emission source",
            "enum": [
                "compliant",
                "non_compliant",
                "under_investigation",
                "pending_permit",
                "all"
            ],
            "default": "all"
        },
        "min_emission": {
            "type": "number",
            "description": "Optional: Minimum annual emission quantity in metric tons to filter results"
        },
        "max_emission": {
            "type": "number",
            "description": "Optional: Maximum annual emission quantity in metric tons to filter results"
        },
        "year": {
            "type": "integer",
            "description": "Optional: Reporting year for emission data (e.g., 2023). Defaults to the most recent available year if not specified.",
            "minimum": 2000,
            "maximum": 2030
        },
        "page": {
            "type": "integer",
            "description": "Optional: Page number for paginated results (1-based indexing). Defaults to 1.",
            "minimum": 1,
            "default": 1
        },
        "page_size": {
            "type": "integer",
            "description": "Optional: Number of results per page (max 100). Defaults to 20.",
            "minimum": 1,
            "maximum": 100,
            "default": 20
        }
    },
    "required": [
        "sector",
        "pollutant"
    ]
},
}
