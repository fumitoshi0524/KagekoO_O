"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Book a hotel room for specified dates, confirming availability and returning a reservation confirmation with booking reference."""
    import json
    from datetime import datetime, date

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ["hotel_id", "room_type", "check_in_date", "check_out_date", "guest_name", "email", "adults"]
        for field in required:
            if field not in data or data[field] is None:
                return json.dumps({"error": f"Missing required field: {field}"})

        # Parse and validate dates
        try:
            check_in = datetime.strptime(data["check_in_date"], "%Y-%m-%d").date()
            check_out = datetime.strptime(data["check_out_date"], "%Y-%m-%d").date()
        except ValueError:
            return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

        today = date.today()
        if check_in < today:
            return json.dumps({"error": "Check-in date must be today or in the future."})
        if check_out <= check_in:
            return json.dumps({"error": "Check-out date must be after check-in date."})

        # Validate room type enum
        valid_rooms = ["single", "double", "suite", "family"]
        if data["room_type"] not in valid_rooms:
            return json.dumps({"error": f"Invalid room_type. Must be one of {valid_rooms}."})

        # Validate adults
        adults = data["adults"]
        if not isinstance(adults, int) or adults < 1 or adults > 10:
            return json.dumps({"error": "Adults must be an integer between 1 and 10."})

        # Validate children if provided
        children = data.get("children", 0)
        if children is not None:
            if not isinstance(children, int) or children < 0 or children > 10:
                return json.dumps({"error": "Children must be an integer between 0 and 10."})
        else:
            children = 0

        # Construct a mock booking reference (in real implementation would call API)
        booking_ref = f"BR-{data['hotel_id'][:5].upper()}-{check_in.strftime('%Y%m%d')}-{hash(data['guest_name'] + data['email']) % 10000:04d}"

        # Return confirmation
        result = {
            "status": "confirmed",
            "booking_reference": booking_ref,
            "hotel_id": data["hotel_id"],
            "room_type": data["room_type"],
            "check_in_date": data["check_in_date"],
            "check_out_date": data["check_out_date"],
            "guest_name": data["guest_name"],
            "email": data["email"],
            "adults": adults,
            "children": children,
            "nights": (check_out - check_in).days
        }
        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload."})
    except Exception as e:
        return json.dumps({"error": f"Internal error: {str(e)}"})


TOOL_SPEC = {
    "name": "book_hotel",
    "description": "Book a hotel room for specified dates, confirming availability and returning a reservation confirmation with booking reference.",
    "category": "operations",
    "domain": "travel",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "hotel_id": {
            "type": "string",
            "description": "Unique identifier of the hotel to book (e.g., 'HILTON123', 'MARRIOTT456')"
        },
        "room_type": {
            "type": "string",
            "enum": [
                "single",
                "double",
                "suite",
                "family"
            ],
            "description": "Type of room requested"
        },
        "check_in_date": {
            "type": "string",
            "description": "Check-in date in YYYY-MM-DD format"
        },
        "check_out_date": {
            "type": "string",
            "description": "Check-out date in YYYY-MM-DD format"
        },
        "guest_name": {
            "type": "string",
            "description": "Full name of the primary guest"
        },
        "email": {
            "type": "string",
            "description": "Guest email address for confirmation"
        },
        "adults": {
            "type": "integer",
            "description": "Number of adult guests (1-10)"
        },
        "children": {
            "type": "integer",
            "description": "Optional: Number of children (0-10)"
        }
    },
    "required": [
        "hotel_id",
        "room_type",
        "check_in_date",
        "check_out_date",
        "guest_name",
        "email",
        "adults"
    ]
},
}
