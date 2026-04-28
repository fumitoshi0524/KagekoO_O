"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Export a filtered segment of customer records from the enterprise CRM system based on demographic, purchase history, and engagement criteria, returning a downloadable CSV file reference with record count summary."""
    import json
    from datetime import datetime, timedelta
    import os
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ["segment_name", "min_purchase_count", "max_purchase_count", "min_total_spent", "max_total_spent", "min_last_purchase_days", "max_last_purchase_days"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        segment_name = data["segment_name"]
        min_purchase = data["min_purchase_count"]
        max_purchase = data["max_purchase_count"]
        min_spent = data["min_total_spent"]
        max_spent = data["max_total_spent"]
        min_last_purchase = data["min_last_purchase_days"]
        max_last_purchase = data["max_last_purchase_days"]
        include_inactive = data.get("include_inactive", False)
        file_format = data.get("file_format", "csv")
        
        if min_purchase < 0 or max_purchase < 0:
            raise ValueError("Purchase count values must be non-negative")
        if min_spent < 0 or max_spent < 0:
            raise ValueError("Total spent values must be non-negative")
        if min_last_purchase < 0 or max_last_purchase < 0:
            raise ValueError("Last purchase days values must be non-negative")
        if file_format not in ["csv", "json", "xlsx"]:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        # Simulate CRM customer database (in production, this queries the actual CRM)
        mock_customers = [
            {"id": 1001, "name": "Acme Corp", "email": "contact@acme.com", "purchases": 12, "total_spent": 45000.00, "last_purchase_days": 15, "active": True},
            {"id": 1002, "name": "Beta Inc", "email": "info@beta.com", "purchases": 5, "total_spent": 12000.50, "last_purchase_days": 60, "active": True},
            {"id": 1003, "name": "Gamma LLC", "email": "support@gamma.com", "purchases": 0, "total_spent": 0.00, "last_purchase_days": 365, "active": False},
            {"id": 1004, "name": "Delta Co", "email": "sales@delta.com", "purchases": 25, "total_spent": 98000.00, "last_purchase_days": 5, "active": True},
            {"id": 1005, "name": "Epsilon Group", "email": "hello@epsilon.com", "purchases": 8, "total_spent": 23000.00, "last_purchase_days": 90, "active": True},
            {"id": 1006, "name": "Zeta Enterprises", "email": "admin@zeta.com", "purchases": 1, "total_spent": 3500.00, "last_purchase_days": 180, "active": True},
            {"id": 1007, "name": "Eta Solutions", "email": "info@eta.com", "purchases": 3, "total_spent": 7800.00, "last_purchase_days": 45, "active": True}
        ]
        
        filtered = []
        for customer in mock_customers:
            if not include_inactive and not customer["active"]:
                continue
            if customer["purchases"] < min_purchase or customer["purchases"] > max_purchase:
                continue
            if customer["total_spent"] < min_spent or customer["total_spent"] > max_spent:
                continue
            if customer["last_purchase_days"] < min_last_purchase or customer["last_purchase_days"] > max_last_purchase:
                continue
            filtered.append(customer)
        
        # Generate export file
        export_dir = "/tmp/crm_exports"
        os.makedirs(export_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{segment_name}_{timestamp}"
        
        if file_format == "csv":
            filepath = os.path.join(export_dir, f"{filename}.csv")
            with open(filepath, "w") as f:
                f.write("id,name,email,purchases,total_spent,last_purchase_days\n")
                for cust in filtered:
                    f.write(f"{cust['id']},{cust['name']},{cust['email']},{cust['purchases']},{cust['total_spent']},{cust['last_purchase_days']}\n")
        elif file_format == "json":
            filepath = os.path.join(export_dir, f"{filename}.json")
            with open(filepath, "w") as f:
                json.dump(filtered, f, indent=2)
        else:
            filepath = os.path.join(export_dir, f"{filename}.xlsx")
            # In a real implementation would write xlsx; here we write a JSON file as placeholder
            filepath = filepath.replace(".xlsx", ".json")
            with open(filepath, "w") as f:
                json.dump(filtered, f, indent=2)
        
        result = {
            "status": "success",
            "file_path": filepath,
            "record_count": len(filtered),
            "filters_applied": {
                "min_purchase_count": min_purchase,
                "max_purchase_count": max_purchase,
                "min_total_spent": min_spent,
                "max_total_spent": max_spent,
                "min_last_purchase_days": min_last_purchase,
                "max_last_purchase_days": max_last_purchase,
                "include_inactive": include_inactive
            },
            "export_timestamp": timestamp,
            "file_format": file_format
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as ve:
        return json.dumps({"status": "error", "message": str(ve)}, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({"status": "error", "message": "Invalid JSON payload provided"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Export failed: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "customer_segment_export",
    "description": "Export a filtered segment of customer records from the enterprise CRM system based on demographic, purchase history, and engagement criteria, returning a downloadable CSV file reference with record count summary.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "segment_name": {
            "type": "string",
            "description": "Label for the exported customer segment, used as the filename prefix"
        },
        "min_purchase_count": {
            "type": "integer",
            "description": "Minimum number of purchases a customer must have made to be included in the export",
            "minimum": 0
        },
        "max_purchase_count": {
            "type": "integer",
            "description": "Maximum number of purchases a customer may have made to be included in the export",
            "minimum": 0
        },
        "min_total_spent": {
            "type": "number",
            "description": "Minimum total amount spent by the customer (in USD) to be included",
            "minimum": 0
        },
        "max_total_spent": {
            "type": "number",
            "description": "Maximum total amount spent by the customer (in USD) to be included",
            "minimum": 0
        },
        "min_last_purchase_days": {
            "type": "integer",
            "description": "Minimum number of days since customer's last purchase (recency filter)",
            "minimum": 0
        },
        "max_last_purchase_days": {
            "type": "integer",
            "description": "Maximum number of days since customer's last purchase (recency filter)",
            "minimum": 0
        },
        "include_inactive": {
            "type": "boolean",
            "description": "Optional: Include customers who have never made a purchase (inactive accounts)",
            "default": false
        },
        "file_format": {
            "type": "string",
            "description": "Optional: Desired output format for the export file",
            "enum": [
                "csv",
                "json",
                "xlsx"
            ],
            "default": "csv"
        }
    },
    "required": [
        "segment_name",
        "min_purchase_count",
        "max_purchase_count",
        "min_total_spent",
        "max_total_spent",
        "min_last_purchase_days",
        "max_last_purchase_days"
    ]
},
}
