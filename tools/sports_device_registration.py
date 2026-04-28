"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    try:
        data = json.loads(payload)
        required = ["device_type", "brand", "model", "serial_number", "purchase_date"]
        for field in required:
            if field not in data or not data[field]:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)
        device_type = data["device_type"]
        brand = data["brand"]
        model = data["model"]
        serial = data["serial_number"]
        purchase_date_str = data["purchase_date"]
        try:
            purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Invalid purchase_date format, expected YYYY-MM-DD"}, ensure_ascii=False)
        warranty_months = data.get("warranty_months", 0)
        if warranty_months < 0:
            return json.dumps({"error": "warranty_months must be non-negative"}, ensure_ascii=False)
        assigned_to = data.get("assigned_to", None)
        location = data.get("location", None)
        warranty_expiry = None
        if warranty_months > 0:
            months = warranty_months
            year = purchase_date.year + (purchase_date.month + months - 1) // 12
            month = (purchase_date.month + months - 1) % 12 + 1
            day = min(purchase_date.day, [31,29 if year%4==0 and (year%100!=0 or year%400==0) else 28,31,30,31,30,31,31,30,31,30,31][month-1])
            warranty_expiry = datetime(year, month, day).strftime("%Y-%m-%d")
        device_id = f"SPT-{device_type[:3].upper()}-{serial[-6:]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result = {
            "device_id": device_id,
            "device_type": device_type,
            "brand": brand,
            "model": model,
            "serial_number": serial,
            "purchase_date": purchase_date_str,
            "warranty_expiry": warranty_expiry,
            "assigned_to": assigned_to,
            "location": location,
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active"
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "sports_device_registration",
    "description": "Register and manage sports equipment and fitness devices in the system inventory, tracking device type, brand, model, purchase date, warranty status, and assignment to users or facilities. Returns a confirmation with the assigned device ID and registration details.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "device_type": {
            "type": "string",
            "enum": [
                "treadmill",
                "elliptical",
                "stationary_bike",
                "dumbbell_set",
                "barbell",
                "kettlebell",
                "resistance_band",
                "yoga_mat",
                "foam_roller",
                "heart_rate_monitor",
                "gps_watch",
                "smart_scale",
                "other"
            ],
            "description": "Category of the sports or fitness device being registered."
        },
        "brand": {
            "type": "string",
            "description": "Manufacturer or brand name of the device."
        },
        "model": {
            "type": "string",
            "description": "Model identifier of the device as provided by the manufacturer."
        },
        "serial_number": {
            "type": "string",
            "description": "Unique serial number assigned by the manufacturer for tracking and warranty purposes."
        },
        "purchase_date": {
            "type": "string",
            "format": "date",
            "description": "Date when the device was purchased, in YYYY-MM-DD format."
        },
        "warranty_months": {
            "type": "integer",
            "minimum": 0,
            "description": "Optional: Number of months the warranty is valid from the purchase date. Set to 0 for no warranty."
        },
        "assigned_to": {
            "type": "string",
            "description": "Optional: Username or facility name to whom the device is assigned. If omitted, the device remains unassigned in inventory."
        },
        "location": {
            "type": "string",
            "description": "Optional: Physical location or room where the device is stored or installed, e.g. 'Main Gym - Zone A'."
        }
    },
    "required": [
        "device_type",
        "brand",
        "model",
        "serial_number",
        "purchase_date"
    ]
},
}
