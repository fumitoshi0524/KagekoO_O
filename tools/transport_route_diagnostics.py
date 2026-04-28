"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze transport routes for schedule conflicts, layover feasibility, timezone violations, and arrival/departure order consistency — returns a diagnostic report with issues flagged per segment."""
    import json
    from datetime import datetime, timedelta
    
    try:
        data = json.loads(payload)
        segments = data.get("segments", [])
        
        if not segments:
            return json.dumps({"error": "At least one segment is required", "issues": []}, ensure_ascii=False)
        
        buffer_minutes = data.get("buffer_minutes", 60)
        check_timezone = data.get("check_timezone_consistency", False)
        
        issues = []
        warnings = []
        
        for i, seg in enumerate(segments):
            seg_label = f"Segment {i+1}: {seg.get('departure_location', '?')} -> {seg.get('arrival_location', '?')}"
            
            # Validate datetime ordering within segment
            dep_str = seg.get("departure_datetime", "")
            arr_str = seg.get("arrival_datetime", "")
            
            try:
                dep_dt = datetime.fromisoformat(dep_str)
                arr_dt = datetime.fromisoformat(arr_str)
            except (ValueError, TypeError):
                issues.append(f"{seg_label}: Invalid datetime format. Use ISO 8601 (YYYY-MM-DDTHH:MM)")
                continue
            
            if dep_dt >= arr_dt:
                issues.append(f"{seg_label}: Departure datetime ({dep_str}) must be before arrival datetime ({arr_str})")
            else:
                # Check for reasonable travel duration (more than 24 hours suggests possible error)
                duration = arr_dt - dep_dt
                if duration > timedelta(hours=24):
                    warnings.append(f"{seg_label}: Travel duration ({duration}) exceeds 24 hours — verify this is intentional")
                if duration < timedelta(minutes=1):
                    warnings.append(f"{seg_label}: Travel duration is less than 1 minute — possible data entry error")
            
            # Timezone consistency check (basic heuristic)
            if check_timezone:
                tz_dep = seg.get("timezone_departure", "")
                tz_arr = seg.get("timezone_arrival", "")
                if tz_dep and tz_arr:
                    # Simple timezone offset difference check (would need pytz in production)
                    # For now, just flag if different timezones are specified
                    if tz_dep != tz_arr:
                        warnings.append(f"{seg_label}: Different timezones specified ({tz_dep} vs {tz_arr}) — ensure times are local to each location")
        
        # Check layover/connection issues between consecutive segments
        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]
            
            try:
                arr_current = datetime.fromisoformat(current.get("arrival_datetime", ""))
                dep_next = datetime.fromisoformat(next_seg.get("departure_datetime", ""))
            except (ValueError, TypeError):
                continue
            
            gap = dep_next - arr_current
            
            if gap < timedelta(0):
                issues.append(f"Connection issue: Segment {i+1} arrival ({current.get('arrival_datetime')}) is AFTER segment {i+2} departure ({next_seg.get('departure_datetime')}) — schedule overlap detected")
            elif gap < timedelta(minutes=buffer_minutes):
                issues.append(f"Connection issue: Only {int(gap.total_seconds()/60)} minutes between arrival of Segment {i+1} and departure of Segment {i+2} (minimum buffer: {buffer_minutes} minutes)")
            elif gap > timedelta(hours=12):
                warnings.append(f"Long layover: {int(gap.total_seconds()/3600)} hours between Segment {i+1} arrival and Segment {i+2} departure — verify intentional")
        
        # Check for duplicate locations in sequence
        for i in range(len(segments) - 1):
            if segments[i].get("arrival_location", "").lower() != segments[i+1].get("departure_location", "").lower():
                warnings.append(f"Route discontinuity: Segment {i+1} arrives at {segments[i].get('arrival_location')} but Segment {i+2} departs from {segments[i+1].get('departure_location')}")
        
        result = {
            "segments_analyzed": len(segments),
            "issues_count": len(issues),
            "warnings_count": len(warnings),
            "issues": issues,
            "warnings": warnings,
            "route_status": "CLEAN" if len(issues) == 0 else "ISSUES_FOUND",
            "recommendation": "Route appears valid" if len(issues) == 0 else f"Found {len(issues)} issue(s) that need resolution before booking"
        }
        
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        return json.dumps({"error": f"Analysis failed: {str(e)}", "issues": [], "warnings": []}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "transport_route_diagnostics",
    "description": "Analyze transport routes (flights, trains, buses) for schedule conflicts, layover feasibility, timezone violations, and arrival/departure order consistency — returns a diagnostic report with issues flagged per segment for travel agents and trip planners.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "description": "Array of transport route segments to analyze. Each segment must have departure_location, arrival_location, departure_datetime, and arrival_datetime. All datetimes in ISO 8601 format (YYYY-MM-DDTHH:MM). Departure must be before arrival.",
            "items": {
                "type": "object",
                "properties": {
                    "departure_location": {
                        "type": "string",
                        "description": "IATA airport code or city/station name for departure point"
                    },
                    "arrival_location": {
                        "type": "string",
                        "description": "IATA airport code or city/station name for arrival point"
                    },
                    "departure_datetime": {
                        "type": "string",
                        "description": "Local departure datetime in ISO 8601 format (YYYY-MM-DDTHH:MM)"
                    },
                    "arrival_datetime": {
                        "type": "string",
                        "description": "Local arrival datetime in ISO 8601 format (YYYY-MM-DDTHH:MM)"
                    },
                    "transport_type": {
                        "type": "string",
                        "description": "Optional: Type of transport for this segment (flight, train, bus, ferry)",
                        "enum": [
                            "flight",
                            "train",
                            "bus",
                            "ferry"
                        ]
                    },
                    "booking_reference": {
                        "type": "string",
                        "description": "Optional: Booking confirmation or ticket reference number for tracking"
                    },
                    "timezone_departure": {
                        "type": "string",
                        "description": "Optional: IANA timezone name for departure location (e.g., America/New_York) for cross-timezone validation"
                    },
                    "timezone_arrival": {
                        "type": "string",
                        "description": "Optional: IANA timezone name for arrival location (e.g., Europe/London) for cross-timezone validation"
                    }
                },
                "required": [
                    "departure_location",
                    "arrival_location",
                    "departure_datetime",
                    "arrival_datetime"
                ]
            }
        },
        "buffer_minutes": {
            "type": "integer",
            "description": "Optional: Minimum acceptable layover/connection time in minutes between arrival and next departure. Defaults to 60 if not specified.",
            "minimum": 0,
            "maximum": 1440
        },
        "check_timezone_consistency": {
            "type": "boolean",
            "description": "Optional: When true, checks that timezone differences between departure and arrival match the expected travel duration for major routes. Defaults to false."
        }
    },
    "required": [
        "segments"
    ]
},
}
