"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        device_ids = data.get('device_ids')
        maintenance_records = data.get('maintenance_records')
        compliance_standard = data.get('compliance_standard')
        
        if not device_ids or not maintenance_records or not compliance_standard:
            return 'error: Missing required fields'
        
        # Define maintenance intervals by device category (simplified example)
        standard_intervals = {
            'ISO_13485': 365,
            'FDA_21_CFR_820': 180,
            'EU_MDR': 365,
            'JCI': 180
        }
        max_days = standard_intervals.get(compliance_standard, 365)
        
        results = []
        for device_id in device_ids:
            device_records = [r for r in maintenance_records if r.get('device_id') == device_id]
            
            if not device_records:
                results.append({
                    'device_id': device_id,
                    'status': 'critical',
                    'message': 'No maintenance records found for device',
                    'checks': []
                })
                continue
            
            checks = []
            latest_service = max(device_records, key=lambda x: x.get('last_service_date', '1900-01-01'))
            
            # Check 1: Recent maintenance
            try:
                service_date = datetime.strptime(latest_service['last_service_date'], '%Y-%m-%d')
                days_since_service = (datetime.now() - service_date).days
                if days_since_service <= max_days:
                    checks.append({'check': 'recent_maintenance', 'status': 'passed', 'detail': f'Maintained {days_since_service} days ago'})
                else:
                    checks.append({'check': 'recent_maintenance', 'status': 'warning', 'detail': f'Overdue by {days_since_service - max_days} days'})
            except:
                checks.append({'check': 'recent_maintenance', 'status': 'error', 'detail': 'Invalid date format'})
            
            # Check 2: Required fields present
            for idx, record in enumerate(device_records):
                missing = []
                for field in ['service_type', 'technician_id']:
                    if not record.get(field):
                        missing.append(field)
                if missing:
                    checks.append({'check': f'required_fields_record_{idx}', 'status': 'warning', 'detail': f'Missing fields: {", ".join(missing)}'})
            
            # Check 3: Parts replacement documentation
            for idx, record in enumerate(device_records):
                if record.get('parts_replaced'):
                    if len(record['parts_replaced']) > 0:
                        checks.append({'check': f'parts_documented_record_{idx}', 'status': 'passed', 'detail': f'{len(record["parts_replaced"])} parts replaced and documented'})
            
            # Determine overall status
            critical_checks = [c for c in checks if c['status'] == 'error']
            warning_checks = [c for c in checks if c['status'] == 'warning']
            
            if critical_checks:
                overall_status = 'critical'
                message = 'Critical compliance failures detected'
            elif warning_checks:
                overall_status = 'warning'
                message = 'Non-critical compliance issues found'
            else:
                overall_status = 'passed'
                message = 'All compliance checks passed'
            
            results.append({
                'device_id': device_id,
                'status': overall_status,
                'message': message,
                'checks': checks,
                'compliance_standard': compliance_standard
            })
        
        return json.dumps({'results': results, 'compliance_standard': compliance_standard, 'total_devices': len(device_ids), 'timestamp': datetime.now().isoformat()}, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "maintenance_log_verifier",
    "description": "Verify and validate medical device maintenance logs against regulatory compliance standards and manufacturer specifications. Returns a structured compliance report showing passed checks, warnings, and critical failures for each device in the maintenance schedule.",
    "category": "system",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "device_ids": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of medical device identifiers to verify maintenance logs for"
        },
        "maintenance_records": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier matching one in device_ids"
                    },
                    "last_service_date": {
                        "type": "string",
                        "description": "Date of last maintenance in YYYY-MM-DD format"
                    },
                    "service_type": {
                        "type": "string",
                        "description": "Type of maintenance performed"
                    },
                    "technician_id": {
                        "type": "string",
                        "description": "Identifier of the technician who performed service"
                    },
                    "parts_replaced": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of replaced part numbers"
                    }
                }
            },
            "description": "Array of maintenance records to verify"
        },
        "compliance_standard": {
            "type": "string",
            "enum": [
                "ISO_13485",
                "FDA_21_CFR_820",
                "EU_MDR",
                "JCI"
            ],
            "description": "The regulatory compliance standard to validate against"
        }
    },
    "required": [
        "device_ids",
        "maintenance_records",
        "compliance_standard"
    ]
},
}
