"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Validate airline boarding pass data."""
    import json
    import re
    try:
        data = json.loads(payload)
        # Validate required fields
        required = ["passenger_name", "flight_number", "departure_airport", "arrival_airport", "travel_date", "seat"]
        for field in required:
            if field not in data:
                return f'error: Missing required field "{field}"'\
        
        name = data["passenger_name"].strip()
        flight = data["flight_number"].strip().upper()
        dep = data["departure_airport"].strip().upper()
        arr = data["arrival_airport"].strip().upper()
        date = data["travel_date"].strip()
        seat = data["seat"].strip().upper()
        
        # Validation logic
        report = {}
        
        # Name validation: must be non-empty and contain a slash (format LAST/FIRST)
        if not name or "/" not in name:
            report["passenger_name"] = {"status": "fail", "reason": "Name must be in LAST/FIRST format with a slash"}
        else:
            parts = name.split("/")
            if len(parts) != 2 or not all(part.isalpha() for part in parts):
                report["passenger_name"] = {"status": "fail", "reason": "Name parts must contain only letters"}
            else:
                report["passenger_name"] = {"status": "pass"}
        
        # Flight number validation: 2 alpha + 1-4 digits
        flight_pattern = r"^[A-Z]{2}\d{1,4}$"
        if re.match(flight_pattern, flight):
            report["flight_number"] = {"status": "pass"}
        else:
            report["flight_number"] = {"status": "fail", "reason": "Must be 2-letter airline code followed by 1-4 digits"}
        
        # Airport code validation: 3 uppercase letters
        airport_pattern = r"^[A-Z]{3}$"
        if re.match(airport_pattern, dep):
            report["departure_airport"] = {"status": "pass"}
        else:
            report["departure_airport"] = {"status": "fail", "reason": "Must be a valid 3-letter IATA code"}
        
        if re.match(airport_pattern, arr):
            report["arrival_airport"] = {"status": "pass"}
        else:
            report["arrival_airport"] = {"status": "fail", "reason": "Must be a valid 3-letter IATA code"}
        
        # Date validation: YYYY-MM-DD and not in past
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if re.match(date_pattern, date):
            from datetime import datetime, date as dt_date
            try:
                parsed = datetime.strptime(date, "%Y-%m-%d").date()
                if parsed < dt_date.today():
                    report["travel_date"] = {"status": "flag", "reason": "Date is in the past"}
                else:
                    report["travel_date"] = {"status": "pass"}
            except ValueError:
                report["travel_date"] = {"status": "fail", "reason": "Invalid date (e.g., month >12 or day out of range)"}
        else:
            report["travel_date"] = {"status": "fail", "reason": "Must be in YYYY-MM-DD format"}
        
        # Seat validation: 1-2 digits + letter (A-K excluding I)
        seat_pattern = r"^\d{1,2}[A-HJ-K]$"
        if re.match(seat_pattern, seat):
            report["seat"] = {"status": "pass"}
        else:
            report["seat"] = {"status": "fail", "reason": "Must be row number (1-2 digits) + seat letter (A-K, no I)"}
        
        # Overall pass/fail
        all_pass = all(v["status"] == "pass" for v in report.values())
        result = {
            "overall_status": "pass" if all_pass else "fail",
            "validation_details": report
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "boarding_pass_validator",
    "description": "Validate airline boarding pass data by checking passenger name, flight number, departure/arrival airports, date, and seat, returning a structured validation report with pass/flag status for each field.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "passenger_name": {
            "type": "string",
            "description": "Full passenger name as printed on the boarding pass (e.g., 'SMITH/JOHN')."
        },
        "flight_number": {
            "type": "string",
            "description": "Flight number consisting of 2-letter airline code followed by 1-4 digits (e.g., 'AA1234')."
        },
        "departure_airport": {
            "type": "string",
            "description": "IATA 3-letter code for departure airport (e.g., 'JFK')."
        },
        "arrival_airport": {
            "type": "string",
            "description": "IATA 3-letter code for arrival airport (e.g., 'LAX')."
        },
        "travel_date": {
            "type": "string",
            "description": "Travel date in YYYY-MM-DD format (e.g., '2025-03-15')."
        },
        "seat": {
            "type": "string",
            "description": "Seat number (e.g., '14A'). Must match pattern: 1-2 digits followed by a single letter A-K (excluding I)."
        }
    },
    "required": [
        "passenger_name",
        "flight_number",
        "departure_airport",
        "arrival_airport",
        "travel_date",
        "seat"
    ]
},
}
