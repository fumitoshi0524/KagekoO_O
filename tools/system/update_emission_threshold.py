"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Update the regulatory emission threshold for a specific pollutant."""
    import json
    import datetime
    try:
        data = json.loads(payload)
        pollutant_code = data.get('pollutant_code')
        new_threshold_value = data.get('new_threshold_value')
        
        if not pollutant_code or not isinstance(pollutant_code, str):
            return json.dumps({'error': 'pollutant_code is required and must be a string'}, ensure_ascii=False)
        
        if new_threshold_value is None or not isinstance(new_threshold_value, (int, float)):
            return json.dumps({'error': 'new_threshold_value is required and must be a number'}, ensure_ascii=False)
        
        if new_threshold_value < 0:
            return json.dumps({'error': 'new_threshold_value must be a non-negative number'}, ensure_ascii=False)
        
        valid_pollutants = ['CO2', 'NOx', 'SO2', 'PM10', 'CH4', 'NH3', 'VOC', 'CO', 'Pb', 'Hg']
        if pollutant_code.upper() not in [p.upper() for p in valid_pollutants]:
            return json.dumps({'error': f'Unknown pollutant: {pollutant_code}. Valid codes: {valid_pollutants}'}, ensure_ascii=False)
        
        effective_date = data.get('effective_date')
        if effective_date:
            try:
                datetime.date.fromisoformat(effective_date)
            except ValueError:
                return json.dumps({'error': 'effective_date must be in YYYY-MM-DD format'}, ensure_ascii=False)
        else:
            effective_date = datetime.date.today().isoformat()
        
        reason = data.get('reason', 'No reason provided')
        
        result = {
            'status': 'success',
            'message': f"Emission threshold for {pollutant_code.upper()} updated to {new_threshold_value} metric tons/year",
            'pollutant_code': pollutant_code.upper(),
            'old_threshold': None,
            'new_threshold': new_threshold_value,
            'effective_date': effective_date,
            'reason': reason,
            'updated_at': datetime.datetime.now().isoformat()
        }
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "update_emission_threshold",
    "description": "Update the regulatory emission threshold for a specific pollutant in the environmental monitoring system. Operates on pollutant records and threshold policy documents. Returns a confirmation message with the updated threshold value and applicable pollutant code. Used for maintaining compliance with evolving environmental regulations.",
    "category": "system",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "pollutant_code": {
            "type": "string",
            "description": "Standard code identifying the pollutant (e.g., 'CO2', 'NOx', 'SO2', 'PM10', 'CH4'). Must be a recognized environmental pollutant identifier.",
            "examples": [
                "CO2",
                "NOx",
                "SO2",
                "PM10",
                "CH4"
            ]
        },
        "new_threshold_value": {
            "type": "number",
            "description": "The new emission threshold in metric tons per year. Must be a non-negative number.",
            "examples": [
                5000,
                1200.5,
                300
            ]
        },
        "effective_date": {
            "type": "string",
            "description": "Optional: Date when the threshold becomes effective in ISO 8601 format (YYYY-MM-DD). If not provided, the threshold takes effect immediately.",
            "examples": [
                "2025-01-01",
                "2025-07-15"
            ]
        },
        "reason": {
            "type": "string",
            "description": "Optional: Brief explanation for the threshold update (e.g., regulatory change, new scientific evidence).",
            "examples": [
                "Updated EU regulation 2025/1234",
                "New health impact study published"
            ]
        }
    },
    "required": [
        "pollutant_code",
        "new_threshold_value"
    ]
},
}
