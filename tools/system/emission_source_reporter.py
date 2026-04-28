"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime

    # In-memory store for demonstration (use database in production)
    _sources = {}
    _readings = []

    try:
        data = json.loads(payload)
        action = data.get('action')

        if action == 'register_source':
            required = ['source_name', 'facility', 'latitude', 'longitude', 'pollutant', 'permitted_limit']
            missing = [f for f in required if f not in data]
            if missing:
                return json.dumps({'error': f'Missing required fields: {missing}'}, ensure_ascii=False)
            sid = data.get('source_id', ''.join(__import__('random').choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3)) + ''.join(__import__('random').choices('0123456789', k=6)))
            _sources[sid] = {
                'source_id': sid,
                'source_name': data['source_name'],
                'facility': data['facility'],
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'pollutant': data['pollutant'],
                'permitted_limit': data['permitted_limit'],
                'last_updated': datetime.now().isoformat()
            }
            return json.dumps({'status': 'registered', 'source_id': sid, 'source': _sources[sid]}, ensure_ascii=False)

        elif action == 'update_reading':
            required = ['source_id', 'pollutant', 'actual_reading', 'reading_date']
            missing = [f for f in required if f not in data]
            if missing:
                return json.dumps({'error': f'Missing required fields: {missing}'}, ensure_ascii=False)
            sid = data['source_id']
            if sid not in _sources:
                return json.dumps({'error': 'Source not found'}, ensure_ascii=False)
            try:
                datetime.strptime(data['reading_date'], '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'Invalid date format, expected YYYY-MM-DD'}, ensure_ascii=False)
            reading = {
                'source_id': sid,
                'pollutant': data['pollutant'],
                'actual_reading': data['actual_reading'],
                'reading_date': data['reading_date'],
                'timestamp': datetime.now().isoformat()
            }
            limit = _sources[sid]['permitted_limit']
            reading['compliance_status'] = 'compliant' if data['actual_reading'] <= limit else 'non_compliant'
            _readings.append(reading)
            _sources[sid]['last_updated'] = datetime.now().isoformat()
            return json.dumps({'status': 'reading_recorded', 'reading': reading}, ensure_ascii=False)

        elif action == 'query_source':
            sid = data.get('source_id')
            if not sid:
                return json.dumps({'error': 'source_id required'}, ensure_ascii=False)
            if sid not in _sources:
                return json.dumps({'error': 'Source not found'}, ensure_ascii=False)
            source = _sources[sid].copy()
            source_readings = [r for r in _readings if r['source_id'] == sid]
            source['recent_readings'] = source_readings[-10:] if source_readings else []
            return json.dumps({'source': source}, ensure_ascii=False)

        elif action == 'list_non_compliant':
            non_compliant = []
            for r in _readings:
                if r['compliance_status'] == 'non_compliant' and r not in non_compliant:
                    non_compliant.append(r)
            return json.dumps({'non_compliant_readings': non_compliant, 'count': len(non_compliant)}, ensure_ascii=False)

        else:
            return json.dumps({'error': f'Invalid action: {action}'}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "emission_source_reporter",
    "description": "Register, update, and query stationary emission sources (e.g., factory stacks, generators) with their permitted emission limits, actual pollutant readings, and compliance status for environmental regulatory reporting.",
    "category": "system",
    "domain": "environment",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "register_source",
                "update_reading",
                "query_source",
                "list_non_compliant"
            ],
            "description": "Operation to perform: register a new source, submit a daily reading, retrieve source details by ID, or list all sources currently exceeding permitted limits."
        },
        "source_id": {
            "type": "string",
            "pattern": "^[A-Z]{3}\\d{6}$",
            "description": "Unique alphanumeric identifier for the emission source (e.g., 'FAC123456'). Required for update and query operations."
        },
        "source_name": {
            "type": "string",
            "maxLength": 200,
            "description": "Human-readable name of the emission source, e.g., 'Main Boiler Stack'. Required for register_source."
        },
        "facility": {
            "type": "string",
            "maxLength": 100,
            "description": "Name of the facility or plant where the source is located. Required for register_source."
        },
        "latitude": {
            "type": "number",
            "minimum": -90,
            "maximum": 90,
            "description": "Geographic latitude in decimal degrees (WGS84) of the source location. Required for register_source."
        },
        "longitude": {
            "type": "number",
            "minimum": -180,
            "maximum": 180,
            "description": "Geographic longitude in decimal degrees (WGS84) of the source location. Required for register_source."
        },
        "pollutant": {
            "type": "string",
            "enum": [
                "CO2",
                "SOx",
                "NOx",
                "PM10",
                "PM2.5",
                "VOC"
            ],
            "description": "Pollutant type for the reading or limit. Required for register_source and update_reading."
        },
        "permitted_limit": {
            "type": "number",
            "minimum": 0,
            "description": "Maximum allowed emission in kilograms per day for the specified pollutant. Required for register_source."
        },
        "actual_reading": {
            "type": "number",
            "minimum": 0,
            "description": "Measured emission amount in kilograms for the reading period. Required for update_reading."
        },
        "reading_date": {
            "type": "string",
            "format": "date",
            "description": "Date of the emission reading in ISO 8601 format (YYYY-MM-DD). Required for update_reading."
        }
    },
    "required": [
        "action"
    ]
},
}
