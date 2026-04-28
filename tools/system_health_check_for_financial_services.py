"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Assess the operational health of a financial system or service."""
    import json
    from datetime import datetime, timedelta
    import random
    import time

    try:
        data = json.loads(payload)
        system_name = data.get('system_name')
        if not system_name:
            return 'error: system_name is required'
        check_type = data.get('check_type', 'full')
        time_window = data.get('time_window_minutes', 60)
        if not isinstance(time_window, int) or time_window < 1:
            time_window = 60
        if time_window > 1440:
            time_window = 1440

        simulated_db = {
            'payment_gateway': {'uptime': 99.97, 'avg_latency_ms': 120, 'error_rate': 0.01, 'last_alert': None, 'status': 'healthy'},
            'trading_engine': {'uptime': 99.85, 'avg_latency_ms': 45, 'error_rate': 0.05, 'last_alert': '2023-11-20 14:32: latency spike', 'status': 'degraded'},
            'ledger_service': {'uptime': 100.0, 'avg_latency_ms': 80, 'error_rate': 0.0, 'last_alert': None, 'status': 'healthy'},
            'fraud_detection': {'uptime': 98.50, 'avg_latency_ms': 200, 'error_rate': 0.20, 'last_alert': '2023-11-21 09:15: high error rate', 'status': 'critical'},
        }

        if system_name not in simulated_db:
            return json.dumps({'error': f'Unknown system: {system_name}', 'available_systems': list(simulated_db.keys())}, ensure_ascii=False)

        base = simulated_db[system_name]
        now = datetime.utcnow()
        start_time = now - timedelta(minutes=time_window)

        result = {
            'system': system_name,
            'timestamp': now.isoformat() + 'Z',
            'time_window_minutes': time_window,
            'overall_status': base['status'],
            'uptime_percentage': base['uptime'],
            'check_results': []
        }

        if check_type in ['connectivity', 'full']:
            connectivity = random.uniform(0.95, 1.0) > 0.02
            result['check_results'].append({
                'check': 'connectivity',
                'successful': connectivity,
                'detail': 'Reachable with TCP handshake < 50ms' if connectivity else 'Connection timeout after 5s'
            })

        if check_type in ['latency', 'full']:
            jitter = random.uniform(-15, 15)
            latency = max(5, base['avg_latency_ms'] + jitter)
            result['check_results'].append({
                'check': 'latency',
                'avg_response_time_ms': round(latency, 1),
                'threshold_ms': 150,
                'passed': latency < 150
            })

        if check_type in ['errors', 'full']:
            recent_errors = round(base['error_rate'] * time_window * random.uniform(0.8, 1.2))
            result['check_results'].append({
                'check': 'error_rate',
                'recent_errors_est': recent_errors,
                'error_rate_percent': base['error_rate'],
                'threshold_percent': 0.1,
                'passed': base['error_rate'] < 0.1
            })

        if base['last_alert']:
            result['active_alerts'] = [{'time': base['last_alert'].split(': ')[0], 'message': base['last_alert'].split(': ')[1]}]
        else:
            result['active_alerts'] = []

        overall_passed = all(r.get('passed', True) for r in result['check_results'])
        if not overall_passed and result['overall_status'] == 'healthy':
            result['overall_status'] = 'degraded'

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "system_health_check_for_financial_services",
    "description": "Assess the operational health of a financial system or service by checking connectivity, transaction processing latency, and recent error rates, returning a status report including uptime percentage, average response time, and any active alerts for system administrators.",
    "category": "system",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "system_name": {
            "type": "string",
            "description": "Identifier of the financial system or service to check (e.g., payment_gateway, trading_engine, ledger_service)."
        },
        "check_type": {
            "type": "string",
            "description": "Type of health check to perform.",
            "enum": [
                "connectivity",
                "latency",
                "errors",
                "full"
            ],
            "default": "full"
        },
        "time_window_minutes": {
            "type": "integer",
            "description": "Optional: Time window in minutes for analyzing recent error rates and latency (1 to 1440, default 60)."
        }
    },
    "required": [
        "system_name"
    ]
},
}
