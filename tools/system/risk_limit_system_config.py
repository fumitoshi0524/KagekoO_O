"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        account_id = data.get('account_id')
        max_position_size = data.get('max_position_size')
        max_leverage = data.get('max_leverage')
        stop_loss_pct = data.get('stop_loss_pct')
        if not account_id or max_position_size is None or max_leverage is None or stop_loss_pct is None:
            return json.dumps({'error': 'Missing required parameters'}, ensure_ascii=False)
        if max_position_size <= 0:
            return json.dumps({'error': 'max_position_size must be positive'}, ensure_ascii=False)
        if max_leverage < 1:
            return json.dumps({'error': 'max_leverage must be >= 1'}, ensure_ascii=False)
        if not (0 <= stop_loss_pct <= 100):
            return json.dumps({'error': 'stop_loss_pct must be 0-100'}, ensure_ascii=False)
        daily_loss_limit = data.get('daily_loss_limit')
        if daily_loss_limit is not None and daily_loss_limit < 0:
            return json.dumps({'error': 'daily_loss_limit cannot be negative'}, ensure_ascii=False)
        allowed_instruments = data.get('allowed_instruments', [])
        for inst in allowed_instruments:
            if not isinstance(inst, str) or '/' not in inst:
                return json.dumps({'error': f'Invalid instrument: {inst}'}, ensure_ascii=False)
        # Simulate updating configuration (real system would persist)
        result = {
            'account_id': account_id,
            'limits_configured': {
                'max_position_size': max_position_size,
                'max_leverage': max_leverage,
                'stop_loss_pct': stop_loss_pct
            },
            'optional_limits': {},
            'status': 'active'
        }
        if daily_loss_limit is not None:
            result['optional_limits']['daily_loss_limit'] = daily_loss_limit
        if allowed_instruments:
            result['optional_limits']['allowed_instruments'] = allowed_instruments
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "risk_limit_system_config",
    "description": "Configure risk limit parameters for trading accounts, including maximum position size, leverage ratio, and stop-loss thresholds, returning updated limit settings and validation results.",
    "category": "system",
    "domain": "finance",
    "risk_level": "write",
    "schema": {
    "type": "object",
    "properties": {
        "account_id": {
            "type": "string",
            "description": "Unique identifier of the trading account to configure"
        },
        "max_position_size": {
            "type": "number",
            "description": "Maximum allowed position size in base currency units (positive number)"
        },
        "max_leverage": {
            "type": "number",
            "description": "Maximum leverage ratio allowed, e.g. 10 means 10:1 (must be >= 1)"
        },
        "stop_loss_pct": {
            "type": "number",
            "description": "Stop-loss threshold as percentage of account equity (0 to 100)"
        },
        "daily_loss_limit": {
            "type": "number",
            "description": "Optional: Maximum allowable daily loss in base currency units"
        },
        "allowed_instruments": {
            "type": "array",
            "description": "Optional: List of instrument symbols (e.g., EUR/USD) to restrict trading to",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "account_id",
        "max_position_size",
        "max_leverage",
        "stop_loss_pct"
    ]
},
}
