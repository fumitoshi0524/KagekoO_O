"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Query audit logs for financial system actions."""
    import json
    from datetime import datetime

    try:
        data = json.loads(payload)
        required = ["start_date", "end_date"]
        for field in required:
            if field not in data:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)

        start_date = data["start_date"]
        end_date = data["end_date"]

        # Validate date formats
        try:
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            return json.dumps({"error": "Invalid date format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)."}, ensure_ascii=False)

        # Simulate audit log data (in production, query a real database or log service)
        mock_logs = [
            {"id": 1, "timestamp": "2024-01-15T10:30:00Z", "user_id": "user_001", "action": "LOGIN", "resource": "USER", "resource_id": "user_001", "severity": "INFO", "details": "User logged in"},
            {"id": 2, "timestamp": "2024-01-15T10:31:00Z", "user_id": "user_001", "action": "READ", "resource": "ACCOUNT", "resource_id": "acc_12345", "severity": "INFO", "details": "Viewed account balance"},
            {"id": 3, "timestamp": "2024-01-15T10:32:00Z", "user_id": "user_001", "action": "PAYMENT", "resource": "TRANSACTION", "resource_id": "txn_98765", "severity": "INFO", "details": "Payment of $150.00 to vendor A"},
            {"id": 4, "timestamp": "2024-01-15T10:33:00Z", "user_id": "user_002", "action": "UPDATE", "resource": "INVESTMENT", "resource_id": "inv_54321", "severity": "WARNING", "details": "Modified investment portfolio risk level"},
            {"id": 5, "timestamp": "2024-01-15T10:34:00Z", "user_id": "user_003", "action": "DELETE", "resource": "BUDGET", "resource_id": "bud_11111", "severity": "ERROR", "details": "Deleted budget without proper authorization"},
        ]

        # Filter by date range
        filtered = [log for log in mock_logs if start_date <= log["timestamp"] <= end_date]

        # Additional filters
        if "user_id" in data and data["user_id"]:
            filtered = [log for log in filtered if log["user_id"] == data["user_id"]]
        if "action_type" in data and data["action_type"]:
            filtered = [log for log in filtered if log["action"] == data["action_type"]]
        if "resource_type" in data and data["resource_type"]:
            filtered = [log for log in filtered if log["resource"] == data["resource_type"]]
        if "severity" in data and data["severity"]:
            filtered = [log for log in filtered if log["severity"] == data["severity"]]

        # Pagination
        page = data.get("page", 1)
        page_size = min(data.get("page_size", 50), 200)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered[start_idx:end_idx]

        result = {
            "total_entries": len(filtered),
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (len(filtered) + page_size - 1) // page_size),
            "logs": paginated
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"An error occurred: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "audit_log_query",
    "description": "Query and filter system audit logs for financial transactions and user actions, returning a paginated list of log entries with timestamps, user IDs, actions, and resource identifiers for compliance monitoring and security investigations.",
    "category": "system",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "start_date": {
            "type": "string",
            "description": "Start date for the audit log search range in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).",
            "format": "date-time"
        },
        "end_date": {
            "type": "string",
            "description": "End date for the audit log search range in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).",
            "format": "date-time"
        },
        "user_id": {
            "type": "string",
            "description": "Optional: Filter logs by a specific user ID (e.g., employee ID, customer account number)."
        },
        "action_type": {
            "type": "string",
            "description": "Optional: Filter by action type: 'CREATE', 'UPDATE', 'DELETE', 'READ', 'LOGIN', 'LOGOUT', 'PAYMENT', 'TRANSFER', 'AUTHORIZE'.",
            "enum": [
                "CREATE",
                "UPDATE",
                "DELETE",
                "READ",
                "LOGIN",
                "LOGOUT",
                "PAYMENT",
                "TRANSFER",
                "AUTHORIZE"
            ]
        },
        "resource_type": {
            "type": "string",
            "description": "Optional: Filter by resource type: 'ACCOUNT', 'TRANSACTION', 'USER', 'INVESTMENT', 'LOAN', 'PAYMENT', 'BUDGET', 'REPORT'.",
            "enum": [
                "ACCOUNT",
                "TRANSACTION",
                "USER",
                "INVESTMENT",
                "LOAN",
                "PAYMENT",
                "BUDGET",
                "REPORT"
            ]
        },
        "severity": {
            "type": "string",
            "description": "Optional: Filter by log severity level: 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.",
            "enum": [
                "INFO",
                "WARNING",
                "ERROR",
                "CRITICAL"
            ]
        },
        "page": {
            "type": "integer",
            "description": "Optional: Page number for pagination (default: 1).",
            "minimum": 1
        },
        "page_size": {
            "type": "integer",
            "description": "Optional: Number of log entries per page (default: 50, max: 200).",
            "minimum": 1,
            "maximum": 200
        }
    },
    "required": [
        "start_date",
        "end_date"
    ]
},
}
