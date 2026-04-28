"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        action = data.get("action")
        user_id = data.get("user_id")
        if not action or not user_id:
            return json.dumps({"error": "Missing required fields: action, user_id"}, ensure_ascii=False)
        
        # In-memory subscription store (in production, use database)
        # Simulated persistent store
        if not hasattr(run, "subscriptions"):
            run.subscriptions = {}
        
        if action == "list":
            subs = run.subscriptions.get(user_id, [])
            return json.dumps({"user_id": user_id, "subscriptions": subs}, ensure_ascii=False)
        
        service_name = data.get("service_name")
        if not service_name:
            return json.dumps({"error": "service_name required for add/update/cancel"}, ensure_ascii=False)
        
        if action == "add":
            plan = data.get("plan_tier", "basic")
            start = data.get("start_date", "")
            if user_id not in run.subscriptions:
                run.subscriptions[user_id] = []
            # Check for duplicate
            for sub in run.subscriptions[user_id]:
                if sub["service_name"] == service_name and sub["status"] == "active":
                    return json.dumps({"error": f"Active subscription for {service_name} already exists"}, ensure_ascii=False)
            new_sub = {
                "service_name": service_name,
                "plan_tier": plan,
                "status": "active",
                "start_date": start if start else "2024-01-01",
                "end_date": ""
            }
            run.subscriptions[user_id].append(new_sub)
            return json.dumps({"message": f"Subscription to {service_name} added", "subscriptions": run.subscriptions[user_id]}, ensure_ascii=False)
        
        elif action == "update":
            plan = data.get("plan_tier")
            if not plan:
                return json.dumps({"error": "plan_tier required for update"}, ensure_ascii=False)
            if user_id not in run.subscriptions:
                return json.dumps({"error": "No subscriptions found for user"}, ensure_ascii=False)
            updated = False
            for sub in run.subscriptions[user_id]:
                if sub["service_name"] == service_name and sub["status"] == "active":
                    sub["plan_tier"] = plan
                    updated = True
                    break
            if not updated:
                return json.dumps({"error": f"No active subscription for {service_name}"}, ensure_ascii=False)
            return json.dumps({"message": f"Subscription to {service_name} updated to {plan}", "subscriptions": run.subscriptions[user_id]}, ensure_ascii=False)
        
        elif action == "cancel":
            end_date = data.get("end_date", "")
            if user_id not in run.subscriptions:
                return json.dumps({"error": "No subscriptions found for user"}, ensure_ascii=False)
            canceled = False
            for sub in run.subscriptions[user_id]:
                if sub["service_name"] == service_name and sub["status"] == "active":
                    sub["status"] = "canceled"
                    sub["end_date"] = end_date if end_date else "2024-12-31"
                    canceled = True
                    break
            if not canceled:
                return json.dumps({"error": f"No active subscription for {service_name}"}, ensure_ascii=False)
            return json.dumps({"message": f"Subscription to {service_name} canceled", "subscriptions": run.subscriptions[user_id]}, ensure_ascii=False)
        else:
            return json.dumps({"error": "Invalid action"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "streaming_subscription_manager",
    "description": "Manage streaming service subscriptions by adding new subscriptions, updating plan tiers, canceling subscriptions, or listing all active subscriptions for a user. Returns a confirmation message and the updated subscription list.",
    "category": "operations",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Operation to perform: add, update, cancel, or list",
            "enum": [
                "add",
                "update",
                "cancel",
                "list"
            ]
        },
        "user_id": {
            "type": "string",
            "description": "Unique identifier for the user"
        },
        "service_name": {
            "type": "string",
            "description": "Name of the streaming service (e.g., Netflix, Spotify, Hulu). Optional for list action."
        },
        "plan_tier": {
            "type": "string",
            "description": "Optional: Subscription plan tier (e.g., basic, standard, premium). Required for add and update actions.",
            "enum": [
                "basic",
                "standard",
                "premium"
            ]
        },
        "start_date": {
            "type": "string",
            "description": "Optional: Start date of the subscription in YYYY-MM-DD format. Defaults to current date if not provided."
        },
        "end_date": {
            "type": "string",
            "description": "Optional: End date of the subscription in YYYY-MM-DD format. Required for cancel action."
        }
    },
    "required": [
        "action",
        "user_id"
    ]
},
}
