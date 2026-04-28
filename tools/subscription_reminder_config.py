"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Configure and manage recurring subscription reminders for household services."""
    import json
    from datetime import datetime, timedelta
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ["subscription_name", "billing_cycle", "billing_day", "payment_amount", "currency"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)
        
        # Validate billing_day based on cycle
        cycle = data["billing_cycle"]
        day = data["billing_day"]
        if cycle == "weekly" and (day < 0 or day > 6):
            return json.dumps({"error": "For weekly cycle, billing_day must be 0-6 (Sunday-Saturday)"}, ensure_ascii=False)
        if cycle in ["monthly", "quarterly", "annually"] and (day < 1 or day > 31):
            return json.dumps({"error": "For monthly/quarterly/annually cycles, billing_day must be 1-31"}, ensure_ascii=False)
        
        # Generate reminder dates (next 3 cycles)
        today = datetime.now()
        reminders = []
        current_year = today.year
        current_month = today.month
        
        for i in range(3):
            # Calculate next billing date (simplified)
            if cycle == "weekly":
                days_ahead = (day - today.weekday() + 7) % 7 + (i * 7)
                next_billing = today + timedelta(days=days_ahead)
            elif cycle == "monthly":
                next_month = current_month + i
                year_offset = (next_month - 1) // 12
                month = ((next_month - 1) % 12) + 1
                next_year = current_year + year_offset
                max_day = 28  # Simplified - avoid invalid dates
                safe_day = min(day, max_day)
                next_billing = datetime(next_year, month, safe_day)
            elif cycle == "quarterly":
                next_month = current_month + (i * 3)
                year_offset = (next_month - 1) // 12
                month = ((next_month - 1) % 12) + 1
                next_year = current_year + year_offset
                max_day = 28
                safe_day = min(day, max_day)
                next_billing = datetime(next_year, month, safe_day)
            elif cycle == "annually":
                next_year = current_year + i
                max_day = 28
                safe_day = min(day, max_day)
                next_billing = datetime(next_year, current_month, safe_day)
            
            reminder_days = data.get("reminder_days_before", 3)
            reminder_date = next_billing - timedelta(days=reminder_days)
            
            reminders.append({
                "cycle_number": i + 1,
                "due_date": next_billing.strftime("%Y-%m-%d"),
                "reminder_date": reminder_date.strftime("%Y-%m-%d"),
                "amount": data["payment_amount"],
                "currency": data["currency"]
            })
        
        result = {
            "status": "configured",
            "subscription": {
                "name": data["subscription_name"],
                "billing_cycle": cycle,
                "billing_day": day,
                "auto_pay": data.get("auto_pay_enabled", False),
                "notes": data.get("notes", "")
            },
            "upcoming_reminders": reminders,
            "reminder_configuration": {
                "days_before_due": data.get("reminder_days_before", 3),
                "total_reminders_configured": 3
            },
            "created_at": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "subscription_reminder_config",
    "description": "Configure and manage recurring subscription reminders for household services (utilities, streaming, gym, etc.). Records subscription details, sets reminder schedules, and returns a confirmation of the saved configuration. Used to prevent missed payments and track service renewals.",
    "category": "system",
    "domain": "lifestyle",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "subscription_name": {
            "type": "string",
            "description": "Name of the subscription service (e.g. Netflix, Electric Company, Gym Membership)"
        },
        "billing_cycle": {
            "type": "string",
            "description": "How often the subscription renews",
            "enum": [
                "weekly",
                "monthly",
                "quarterly",
                "annually"
            ]
        },
        "billing_day": {
            "type": "integer",
            "description": "Day of the month the payment is due (1-31). For weekly, use day of week (0=Sunday, 6=Saturday).",
            "minimum": 0,
            "maximum": 31
        },
        "reminder_days_before": {
            "type": "integer",
            "description": "Number of days before due date to send reminder (1-15)",
            "minimum": 1,
            "maximum": 15,
            "default": 3
        },
        "payment_amount": {
            "type": "number",
            "description": "The amount charged per billing cycle in local currency",
            "minimum": 0
        },
        "currency": {
            "type": "string",
            "description": "ISO 4217 currency code (e.g. USD, EUR, GBP)",
            "pattern": "^[A-Z]{3}$"
        },
        "auto_pay_enabled": {
            "type": "boolean",
            "description": "Optional: Whether this subscription uses automatic payment. Defaults to false.",
            "default": false
        },
        "notes": {
            "type": "string",
            "description": "Optional: Free-text notes about the subscription (account number, contact info, etc.)"
        }
    },
    "required": [
        "subscription_name",
        "billing_cycle",
        "billing_day",
        "payment_amount",
        "currency"
    ]
},
}
