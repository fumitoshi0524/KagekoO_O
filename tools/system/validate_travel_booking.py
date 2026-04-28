"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        booking_ref = data.get('booking_reference')
        docs = data.get('passenger_documents')
        check_ssr = data.get('check_ssr_codes', False)
        force = data.get('force_validate', False)
        if not booking_ref or not docs:
            return '{"error": "Missing required fields: booking_reference and passenger_documents"}'
        if not isinstance(docs, dict):
            return '{"error": "passenger_documents must be a dictionary"}'
        # Simulate seat availability check
        available_seats = {'1A', '1B', '2C', '3D', '4E', '5F', '6A', '7B', '8C', '9D'}
        seat_conflicts = []
        status = 'confirmed'
        for idx, doc in docs.items():
            if not isinstance(doc, dict):
                continue
            doc_type = doc.get('type', '')
            doc_number = doc.get('number', '')
            expiry = doc.get('expiry_date', '')
            if doc_type not in ('passport', 'visa', 'id_card'):
                seat_conflicts.append(f'Passenger {idx}: invalid document type {doc_type}')
            if len(doc_number) < 5:
                seat_conflicts.append(f'Passenger {idx}: document number too short')
            # Simulate expiry check (past date check)
            if expiry and expiry < '2026-01-01':
                seat_conflicts.append(f'Passenger {idx}: document expired')
        if seat_conflicts:
            status = 'issues_found'
        # SSR validation
        ssr_results = {}
        if check_ssr:
            valid_ssrs = ['WCHR', 'WCHS', 'WCHC', 'VGML', 'DBML', 'BBML', 'SFML']
            ssr_results['valid_ssrs'] = valid_ssrs
            ssr_results['status'] = 'enabled'
        # Build result
        result = {
            'booking_reference': booking_ref,
            'status': status,
            'total_passengers': len(docs),
            'available_seats': sorted(available_seats),
            'warnings': seat_conflicts,
            'ssr_check': ssr_results,
            'next_steps': 'Please check warnings and confirm booking' if seat_conflicts else 'Booking validated successfully'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'


TOOL_SPEC = {
    "name": "validate_travel_booking",
    "description": "Validate and enrich a travel booking by checking seat availability, verifying passenger documents, confirming special service requests (SSRs), and returning a booking summary with status, warnings, and next steps.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "booking_reference": {
            "type": "string",
            "description": "Alphanumeric booking reference code (e.g., ABC123). Must be 6-10 characters."
        },
        "passenger_documents": {
            "type": "object",
            "description": "Dictionary mapping passenger indices (0-based) to document info: each value is an object with 'type' (passport/visa/id_card), 'number' (string), 'expiry_date' (YYYY-MM-DD)."
        },
        "check_ssr_codes": {
            "type": "boolean",
            "description": "Optional: If True, check and validate special service request codes (wheelchair, meal, etc.).",
            "default": False
        },
        "force_validate": {
            "type": "boolean",
            "description": "Optional: If True, force re-validation even if previously validated.",
            "default": False
        }
    },
    "required": [
        "booking_reference",
        "passenger_documents"
    ]
},
}
