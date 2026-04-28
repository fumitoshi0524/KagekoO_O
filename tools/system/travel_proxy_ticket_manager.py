"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Manage proxy ticket assignments for travel agents."""
    import json
    import uuid
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        action = data.get("action")
        agent_id = data.get("agent_id")

        if not action:
            return json.dumps({"error": "Missing required field: action"}, ensure_ascii=False)
        if not agent_id:
            return json.dumps({"error": "Missing required field: agent_id"}, ensure_ascii=False)

        if action not in ["issue", "revoke", "list", "validate"]:
            return json.dumps({"error": f"Invalid action: {action}. Must be one of: issue, revoke, list, validate"}, ensure_ascii=False)

        if action == "issue":
            session_token = data.get("session_token")
            if not session_token:
                return json.dumps({"error": "session_token is required for issue action"}, ensure_ascii=False)
            if len(session_token) < 16:
                return json.dumps({"error": "session_token must be at least 16 characters"}, ensure_ascii=False)

            new_ticket_id = str(uuid.uuid4())
            now = datetime.utcnow()
            expires_at = (now + timedelta(hours=2)).isoformat() + "Z"

            result = {
                "status": "success",
                "action": "issue",
                "agent_id": agent_id,
                "ticket_id": new_ticket_id,
                "issued_at": now.isoformat() + "Z",
                "expires_at": expires_at,
                "is_active": True,
                "message": "Proxy ticket issued successfully. Valid for 2 hours."
            }
            return json.dumps(result, ensure_ascii=False)

        elif action == "revoke":
            ticket_id = data.get("ticket_id")
            if not ticket_id:
                return json.dumps({"error": "ticket_id is required for revoke action"}, ensure_ascii=False)

            result = {
                "status": "success",
                "action": "revoke",
                "agent_id": agent_id,
                "ticket_id": ticket_id,
                "revoked_at": datetime.utcnow().isoformat() + "Z",
                "is_active": False,
                "message": f"Proxy ticket {ticket_id} revoked successfully."
            }
            return json.dumps(result, ensure_ascii=False)

        elif action == "list":
            result = {
                "status": "success",
                "action": "list",
                "agent_id": agent_id,
                "active_tickets": [
                    {
                        "ticket_id": "ticket_abc123",
                        "issued_at": "2025-03-20T10:30:00Z",
                        "expires_at": "2025-03-20T12:30:00Z",
                        "is_active": True
                    },
                    {
                        "ticket_id": "ticket_def456",
                        "issued_at": "2025-03-20T11:00:00Z",
                        "expires_at": "2025-03-20T13:00:00Z",
                        "is_active": True
                    }
                ],
                "total_count": 2,
                "message": "Active proxy tickets listed."
            }
            return json.dumps(result, ensure_ascii=False)

        elif action == "validate":
            ticket_id = data.get("ticket_id")
            if not ticket_id:
                return json.dumps({"error": "ticket_id is required for validate action"}, ensure_ascii=False)

            result = {
                "status": "success",
                "action": "validate",
                "agent_id": agent_id,
                "ticket_id": ticket_id,
                "is_active": True,
                "validated_at": datetime.utcnow().isoformat() + "Z",
                "session_status": "active",
                "message": "Ticket is valid and session is active."
            }
            return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False)



TOOL_SPEC = {
    "name": "travel_proxy_ticket_manager",
    "description": "Manage proxy ticket assignments for travel agents, including validating agent IDs, checking active session status, issuing new single-use proxy tickets, revoking tickets, and listing all active tickets for an agent. Returns ticket status, agent activity logs, and ticket validity details for secure booking handoffs.",
    "category": "system",
    "domain": "travel",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The operation to perform: issue (create new ticket), revoke (invalidate ticket), list (show all active tickets), validate (check ticket and session status)",
            "enum": [
                "issue",
                "revoke",
                "list",
                "validate"
            ]
        },
        "agent_id": {
            "type": "string",
            "description": "Unique identifier for the travel agent (alphanumeric, 8-20 characters)",
            "pattern": "^[a-zA-Z0-9]{8,20}$"
        },
        "ticket_id": {
            "type": "string",
            "description": "Optional: Proxy ticket token (UUID format only for revoke/validate actions); if not provided for issue, one is auto-generated"
        },
        "session_token": {
            "type": "string",
            "description": "Optional: Session authentication token for agent login validation; required for issue and revoke",
            "minLength": 16
        },
        "notes": {
            "type": "string",
            "description": "Optional: Free-text note to attach to the action (max 200 characters)",
            "maxLength": 200
        }
    },
    "required": [
        "action",
        "agent_id"
    ]
},
}
