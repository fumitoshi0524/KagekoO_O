"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage sports facility membership records."""
    import json
    try:
        data = json.loads(payload)
        action = data.get("action")
        if action not in ["add_member", "update_tier", "list_members", "remove_member"]:
            return json.dumps({"error": "Invalid action. Must be one of: add_member, update_tier, list_members, remove_member"})

        # In-memory storage (in production this would be a database)
        if not hasattr(run, "members"):
            run.members = {}

        if action == "list_members":
            members_list = []
            for mid, minfo in run.members.items():
                members_list.append({
                    "member_id": mid,
                    "member_name": minfo["name"],
                    "tier": minfo["tier"],
                    "email": minfo["email"],
                    "phone": minfo.get("phone", ""),
                    "active": minfo["active"],
                    "expiration": minfo["expiration"]
                })
            return json.dumps({"members": members_list, "count": len(members_list)}, ensure_ascii=False)

        elif action == "add_member":
            member_name = data.get("member_name")
            email = data.get("email")
            if not member_name or not email:
                return json.dumps({"error": "member_name and email are required for add_member"})
            tier = data.get("membership_tier", "basic")
            if tier not in ["basic", "premium", "vip"]:
                return json.dumps({"error": "Invalid tier. Must be basic, premium, or vip"})
            import uuid
            member_id = str(uuid.uuid4())[:8]
            from datetime import datetime, timedelta
            expiration = (datetime.now() + timedelta(days=365)).isoformat()
            run.members[member_id] = {
                "name": member_name,
                "tier": tier,
                "email": email,
                "phone": data.get("phone", ""),
                "active": True,
                "expiration": expiration
            }
            return json.dumps({"status": "success", "message": f"Member {member_name} added with ID {member_id}", "member_id": member_id}, ensure_ascii=False)

        elif action == "update_tier":
            member_id = data.get("member_id")
            new_tier = data.get("membership_tier")
            if not member_id:
                return json.dumps({"error": "member_id is required for update_tier"})
            if not new_tier or new_tier not in ["basic", "premium", "vip"]:
                return json.dumps({"error": "Valid membership_tier (basic, premium, vip) is required"})
            if member_id not in run.members:
                return json.dumps({"error": f"Member {member_id} not found"})
            old_tier = run.members[member_id]["tier"]
            run.members[member_id]["tier"] = new_tier
            return json.dumps({"status": "success", "message": f"Member {run.members[member_id]['name']} tier updated from {old_tier} to {new_tier}"}, ensure_ascii=False)

        elif action == "remove_member":
            member_id = data.get("member_id")
            if not member_id:
                return json.dumps({"error": "member_id is required for remove_member"})
            if member_id not in run.members:
                return json.dumps({"error": f"Member {member_id} not found"})
            removed_name = run.members[member_id]["name"]
            del run.members[member_id]
            return json.dumps({"status": "success", "message": f"Member {removed_name} removed from system"}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)})


TOOL_SPEC = {
    "name": "sports_membership_manager",
    "description": "Manage sports facility membership records by adding new members, updating membership tiers, and listing current members with their subscription status, expiration dates, and access privileges for the sports facility system.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Action to perform on the membership system: add_member, update_tier, list_members, or remove_member",
            "enum": [
                "add_member",
                "update_tier",
                "list_members",
                "remove_member"
            ]
        },
        "member_id": {
            "type": "string",
            "description": "Unique identifier for the sports facility member. Required for update_tier, remove_member actions."
        },
        "member_name": {
            "type": "string",
            "description": "Full name of the member. Required for add_member action."
        },
        "membership_tier": {
            "type": "string",
            "description": "Optional: Membership tier level: basic, premium, or vip. Default is basic for new members."
        },
        "email": {
            "type": "string",
            "description": "Optional: Email address of the member. Required for add_member action."
        },
        "phone": {
            "type": "string",
            "description": "Optional: Phone number of the member."
        }
    },
    "required": [
        "action"
    ]
},
}
