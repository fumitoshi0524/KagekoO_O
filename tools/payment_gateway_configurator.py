"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Configure and validate payment gateway integration settings."""
    import json
    import requests
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ["gateway_name", "merchant_id", "api_key", "api_endpoint", "supported_currencies"]
        for field in required:
            if field not in data or data[field] is None:
                return json.dumps({"error": f"Missing required field: {field}"}, ensure_ascii=False)

        gateway_name = data["gateway_name"]
        merchant_id = data["merchant_id"]
        api_key = data["api_key"]
        api_endpoint = data["api_endpoint"]
        supported_currencies = data["supported_currencies"]
        transaction_limit_per_txn = data.get("transaction_limit_per_transaction", None)
        transaction_limit_daily = data.get("transaction_limit_daily", None)
        test_mode = data.get("test_mode", False)

        # Validate currencies format
        valid_currencies = all(isinstance(c, str) and len(c) == 3 and c.isalpha() for c in supported_currencies)
        if not valid_currencies:
            return json.dumps({"error": "Each currency must be a 3-letter ISO 4217 code (e.g., USD)."}, ensure_ascii=False)
        if len(supported_currencies) == 0:
            return json.dumps({"error": "At least one supported currency is required."}, ensure_ascii=False)

        # Validate API endpoint format
        if not api_endpoint.startswith("https://"):
            return json.dumps({"error": "API endpoint must start with https://."}, ensure_ascii=False)

        # Validate transaction limits
        if transaction_limit_per_txn is not None and transaction_limit_per_txn <= 0:
            return json.dumps({"error": "Transaction limit per transaction must be a positive number."}, ensure_ascii=False)
        if transaction_limit_daily is not None and transaction_limit_daily <= 0:
            return json.dumps({"error": "Daily transaction limit must be a positive number."}, ensure_ascii=False)

        # Simulate connection to payment gateway API (realistic but not actual call)
        test_url = api_endpoint + "/v1/test"
        try:
            if test_mode:
                response = requests.get(test_url, timeout=5)
                gateway_reachable = response.status_code < 500
            else:
                # In production, actual validation with API key
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get(api_endpoint + "/v1/merchant/" + merchant_id, headers=headers, timeout=5)
                gateway_reachable = response.status_code == 200
        except requests.ConnectionError:
            gateway_reachable = False
        except requests.Timeout:
            gateway_reachable = False

        # Build configuration record
        config_id = "cfg_" + datetime.now().strftime("%Y%m%d%H%M%S") + "_" + gateway_name.lower()
        status = "active" if gateway_reachable else "inactive"
        warnings = []
        if not gateway_reachable:
            warnings.append("Payment gateway endpoint not reachable. Configuration saved but may not work.")
        if transaction_limit_per_txn and transaction_limit_daily and transaction_limit_per_txn > transaction_limit_daily:
            warnings.append("Per-transaction limit exceeds daily limit. Daily limit will override.")

        result = {
            "config_id": config_id,
            "gateway_name": gateway_name,
            "merchant_id": merchant_id,
            "api_endpoint": api_endpoint,
            "supported_currencies": supported_currencies,
            "transaction_limits": {
                "per_transaction": transaction_limit_per_txn,
                "daily": transaction_limit_daily
            },
            "test_mode": test_mode,
            "status": status,
            "configured_at": datetime.now().isoformat(),
            "validated": {
                "gateway_reachable": gateway_reachable,
                "currency_format_valid": True,
                "limits_valid": True
            },
            "warnings": warnings
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload."}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "payment_gateway_configurator",
    "description": "Configure and validate payment gateway integration settings for a financial system, including merchant credentials, API endpoints, supported currencies, and transaction limits, and return a configuration status report.",
    "category": "system",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "gateway_name": {
            "type": "string",
            "description": "Name of the payment gateway to configure (e.g., Stripe, PayPal, Square, Adyen)."
        },
        "merchant_id": {
            "type": "string",
            "description": "Unique merchant identifier assigned by the payment gateway for transaction processing."
        },
        "api_key": {
            "type": "string",
            "description": "Secret API key used to authenticate with the payment gateway's services."
        },
        "api_endpoint": {
            "type": "string",
            "description": "Base URL of the payment gateway API endpoint (e.g., https://api.stripe.com/v1)."
        },
        "supported_currencies": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of currency codes (ISO 4217) the gateway will support, e.g., [\"USD\", \"EUR\", \"GBP\"]."
        },
        "transaction_limit_per_transaction": {
            "type": "number",
            "description": "Optional: Maximum authorized amount per single transaction in the base currency (e.g., 10000.00). Leave empty for no limit."
        },
        "transaction_limit_daily": {
            "type": "number",
            "description": "Optional: Maximum total amount of transactions allowed per day in the base currency (e.g., 50000.00). Leave empty for no limit."
        },
        "test_mode": {
            "type": "boolean",
            "description": "Optional: Set to true to enable sandbox/test environment instead of live processing. Defaults to false if not provided."
        }
    },
    "required": [
        "gateway_name",
        "merchant_id",
        "api_key",
        "api_endpoint",
        "supported_currencies"
    ]
},
}
