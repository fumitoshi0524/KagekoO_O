"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import time
    import random
    import statistics
    
    try:
        data = json.loads(payload)
        operation = data.get('operation_type')
        if not operation or operation not in ['athlete_query', 'event_schedule', 'full_suite']:
            return 'error: Invalid or missing operation_type. Must be athlete_query, event_schedule, or full_suite.'
        
        concurrent_users = data.get('concurrent_users', 1)
        duration = data.get('duration_seconds', 10)
        
        if not (1 <= concurrent_users <= 100):
            return 'error: concurrent_users must be between 1 and 100.'
        if not (1 <= duration <= 300):
            return 'error: duration_seconds must be between 1 and 300.'
        
        # Simulate benchmark execution
        start_time = time.time()
        latencies = []
        errors = 0
        total_ops = 0
        
        end_time = start_time + duration
        while time.time() < end_time:
            for _ in range(concurrent_users):
                op_start = time.time()
                # Simulate processing time based on operation
                if operation == 'athlete_query':
                    sim_delay = random.uniform(0.01, 0.2)
                elif operation == 'event_schedule':
                    sim_delay = random.uniform(0.02, 0.3)
                else:  # full_suite
                    sim_delay = random.uniform(0.05, 0.5)
                
                # Simulate occasional error (5% chance)
                if random.random() < 0.05:
                    errors += 1
                else:
                    time.sleep(sim_delay * 0.001)  # simulate tiny work
                    lat = (time.time() - op_start) * 1000  # ms
                    latencies.append(lat)
                total_ops += 1
        
        elapsed = time.time() - start_time
        
        if not latencies:
            return json.dumps({
                'status': 'failure',
                'message': 'No successful operations recorded',
                'total_operations': total_ops,
                'errors': errors
            }, ensure_ascii=False)
        
        throughput = total_ops / elapsed if elapsed > 0 else 0
        result = {
            'status': 'success',
            'operation_type': operation,
            'concurrent_users': concurrent_users,
            'duration_seconds': duration,
            'total_operations': total_ops,
            'errors': errors,
            'error_rate': round(errors / total_ops * 100, 2) if total_ops else 0,
            'throughput_ops_per_second': round(throughput, 2),
            'latency_ms': {
                'min': round(min(latencies), 2),
                'max': round(max(latencies), 2),
                'avg': round(statistics.mean(latencies), 2),
                'median': round(statistics.median(latencies), 2),
                'p95': round(sorted(latencies)[int(len(latencies)*0.95)], 2) if len(latencies) > 1 else round(latencies[0], 2),
                'p99': round(sorted(latencies)[int(len(latencies)*0.99)], 2) if len(latencies) > 1 else round(latencies[0], 2)
            },
            'system_health': {
                'cpu_utilization_percent': round(random.uniform(30, 90), 1),
                'memory_usage_percent': round(random.uniform(40, 85), 1),
                'network_io_mbps': round(random.uniform(10, 200), 1)
            }
        }
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "sports_benchmark_runner",
    "description": "Execute a system-level benchmark test for a sports analytics platform, measuring response times and throughput for common operations like athlete performance queries and event schedule lookups, and return a performance report with latency, error rates, and system health metrics.",
    "category": "system",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "operation_type": {
            "type": "string",
            "description": "Type of benchmark operation to run: 'athlete_query', 'event_schedule', or 'full_suite'. 'full_suite' runs all operations sequentially.",
            "enum": [
                "athlete_query",
                "event_schedule",
                "full_suite"
            ]
        },
        "concurrent_users": {
            "type": "integer",
            "description": "Optional: Number of simulated concurrent users for load testing. Default is 1. Must be between 1 and 100.",
            "minimum": 1,
            "maximum": 100
        },
        "duration_seconds": {
            "type": "integer",
            "description": "Optional: Duration of the benchmark test in seconds. Default is 10. Must be between 1 and 300.",
            "minimum": 1,
            "maximum": 300
        },
        "target_endpoint": {
            "type": "string",
            "description": "Optional: Custom endpoint URL to benchmark. If not provided, uses the default internal sports API endpoint.",
            "format": "uri"
        }
    },
    "required": [
        "operation_type"
    ]
},
}
