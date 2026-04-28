"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Check visa requirements for a traveler based on passport nationality and destination country. Returns visa category, allowed stay duration, required documents, and processing time estimates for tourism purposes."""
    import json
    try:
        data = json.loads(payload)
        passport = data.get('passport_country', '').upper()
        destination = data.get('destination_country', '').upper()
        purpose = data.get('purpose', 'tourism')
        stay_days = data.get('stay_days', 30)

        if not passport or not destination:
            return json.dumps({'error': 'passport_country and destination_country are required'}, ensure_ascii=False)

        if passport == destination:
            return json.dumps({'error': 'Passport and destination countries cannot be the same'}, ensure_ascii=False)

        if len(passport) != 2 or len(destination) != 2:
            return json.dumps({'error': 'Country codes must be exactly 2 uppercase letters'}, ensure_ascii=False)

        # Visa waiver agreements database (simplified real-world mappings)
        visa_free_zones = {
            'US': ['CA', 'MX', 'GB', 'IE', 'DE', 'FR', 'IT', 'ES', 'JP', 'KR', 'SG', 'MY', 'PH', 'IL', 'CL', 'CR', 'PA', 'PE'],
            'GB': ['US', 'CA', 'AU', 'NZ', 'JP', 'KR', 'SG', 'MY', 'TH', 'ID', 'PH', 'VN', 'AE', 'QA', 'BH', 'OM', 'KW', 'SA'],
            'JP': ['US', 'CA', 'GB', 'AU', 'NZ', 'KR', 'SG', 'MY', 'TH', 'ID', 'PH', 'VN', 'AE', 'QA', 'BH', 'OM', 'KW', 'SA'],
            'SG': ['MY', 'TH', 'ID', 'PH', 'VN', 'KH', 'LA', 'MM', 'BN', 'MN', 'NP', 'LK', 'MV', 'SC', 'MU', 'ZA', 'KE', 'TZ', 'UG', 'RW', 'ET', 'DJ', 'SO']
        }

        e_visa_countries = ['TH', 'VN', 'KH', 'LA', 'MM', 'MN', 'NP', 'LK', 'MV', 'SC', 'MU', 'ZA', 'KE', 'TZ', 'UG', 'RW', 'ET', 'DJ', 'SO']
        visa_on_arrival_countries = ['TH', 'VN', 'KH', 'LA', 'MM', 'IN', 'NP', 'LK', 'BD', 'BT', 'MV', 'ID', 'PH', 'TL']

        result = {
            'passport_country': passport,
            'destination_country': destination,
            'purpose': purpose,
            'requested_stay_days': stay_days,
            'visa_required': True,
            'visa_type': 'Unknown',
            'max_stay_days': 0,
            'processing_days': '30-60',
            'required_documents': ['passport valid 6+ months', 'completed application form', 'passport photos', 'flight itinerary', 'hotel booking', 'bank statement'],
            'fee_usd': 0,
            'notes': ''
        }

        # Check visa-free agreements
        if passport in visa_free_zones and destination in visa_free_zones[passport]:
            result['visa_required'] = False
            result['visa_type'] = 'Visa-free'
            result['max_stay_days'] = 30 if stay_days <= 30 else 90
            result['processing_days'] = '0 (immediate)'
            result['required_documents'] = ['passport valid 6+ months', 'return ticket', 'hotel booking']
            result['fee_usd'] = 0
            result['notes'] = 'Visa-free entry granted under bilateral agreement.'
        elif destination in e_visa_countries:
            result['visa_type'] = 'e-Visa'
            result['max_stay_days'] = 30
            result['processing_days'] = '3-7'
            result['fee_usd'] = 50
            result['notes'] = 'Apply online before travel. e-Visa valid for single entry 30 days.'
        elif destination in visa_on_arrival_countries:
            result['visa_type'] = 'Visa on Arrival'
            result['max_stay_days'] = 15
            result['processing_days'] = '0 (at airport)'
            result['fee_usd'] = 30
            result['notes'] = 'Obtain at airport upon arrival. Valid 15 days, extendable once for 7 days.'
        else:
            result['visa_type'] = 'Tourist Visa (Embassy)'
            result['max_stay_days'] = 60
            result['processing_days'] = '15-30'
            result['fee_usd'] = 100
            result['notes'] = 'Apply at embassy/consulate. May require interview. Valid for single or multiple entry up to 6 months.'

        if stay_days > result['max_stay_days'] and result['max_stay_days'] > 0:
            result['notes'] += f' Warning: requested stay ({stay_days} days) exceeds max allowed ({result["max_stay_days"]} days). Valid visa or extension needed.'

        # Document requirements by purpose
        if purpose == 'business':
            result['required_documents'].extend(['invitation letter from host company', 'company registration proof', 'business letter from employer'])
        elif purpose == 'transit':
            result['required_documents'] = ['passport valid 6+ months', 'confirmed onward ticket', 'visa for destination country if required']
            result['max_stay_days'] = 3
            result['fee_usd'] = 20
        elif purpose == 'study':
            result['required_documents'] = ['passport valid 6+ months', 'acceptance letter from institution', 'proof of financial means', 'health insurance', 'police clearance certificate']
            result['max_stay_days'] = 365
            result['fee_usd'] = 150
            result['processing_days'] = '30-90'

        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        return 'error: Invalid JSON payload'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "tourist_visa_expert",
    "description": "Check visa requirements for a traveler based on passport nationality and destination country. Returns visa category, allowed stay duration, required documents, and processing time estimates for tourism purposes.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "passport_country": {
            "type": "string",
            "description": "ISO 3166-1 alpha-2 country code of the traveler's passport (e.g., US, GB, DE). Two uppercase letters only.",
            "examples": [
                "US",
                "GB",
                "DE"
            ]
        },
        "destination_country": {
            "type": "string",
            "description": "ISO 3166-1 alpha-2 country code of the destination (e.g., TH, JP, BR). Two uppercase letters only.",
            "examples": [
                "TH",
                "JP",
                "BR"
            ]
        },
        "purpose": {
            "type": "string",
            "description": "Primary purpose of travel affecting visa type.",
            "enum": [
                "tourism",
                "business",
                "transit",
                "study"
            ],
            "examples": [
                "tourism"
            ]
        },
        "stay_days": {
            "type": "integer",
            "description": "Optional: Expected duration of stay in days (1-365). Used to filter applicable visa types.",
            "minimum": 1,
            "maximum": 365,
            "examples": [
                14,
                30
            ]
        }
    },
    "required": [
        "passport_country",
        "destination_country",
        "purpose"
    ]
},
}
