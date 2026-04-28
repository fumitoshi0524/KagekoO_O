"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import psutil
    import os
    try:
        data = json.loads(payload)
        proc_name = data.get('media_process_name')
        metrics = data.get('metrics')
        if not proc_name or not metrics:
            return json.dumps({'error': 'Missing required parameter: media_process_name and metrics'}, ensure_ascii=False)
        valid_metrics = {'cpu_percent', 'memory_mb', 'disk_read_bytes', 'disk_write_bytes', 'thread_count'}
        for m in metrics:
            if m not in valid_metrics:
                return json.dumps({'error': f'Invalid metric: {m}. Must be one of {valid_metrics}'}, ensure_ascii=False)
        result = {}
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'io_counters', 'num_threads']):
            try:
                if proc_name.lower() in proc.info['name'].lower() if proc.info['name'] else False:
                    proc_data = {'pid': proc.info['pid'], 'name': proc.info['name']}
                    if 'cpu_percent' in metrics:
                        proc_data['cpu_percent'] = proc.info['cpu_percent']
                    if 'memory_mb' in metrics:
                        proc_data['memory_mb'] = round(proc.info['memory_info'].rss / (1024 * 1024), 2)
                    if 'disk_read_bytes' in metrics or 'disk_write_bytes' in metrics:
                        io = proc.info['io_counters']
                        if io:
                            if 'disk_read_bytes' in metrics:
                                proc_data['disk_read_bytes'] = io.read_bytes
                            if 'disk_write_bytes' in metrics:
                                proc_data['disk_write_bytes'] = io.write_bytes
                        else:
                            if 'disk_read_bytes' in metrics:
                                proc_data['disk_read_bytes'] = 0
                            if 'disk_write_bytes' in metrics:
                                proc_data['disk_write_bytes'] = 0
                    if 'thread_count' in metrics:
                        proc_data['thread_count'] = proc.info['num_threads']
                    processes.append(proc_data)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        result['match_count'] = len(processes)
        result['processes'] = processes
        result['total_cpu_percent'] = sum(p.get('cpu_percent', 0) for p in processes if 'cpu_percent' in p)
        result['total_memory_mb'] = sum(p.get('memory_mb', 0) for p in processes if 'memory_mb' in p)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "media_monitor",
    "description": "Query and display current system-level metrics (CPU load, memory usage, disk I/O) specifically for active entertainment/media processes such as video players, streaming apps, and audio services, returning a structured snapshot for performance diagnostics.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "media_process_name": {
            "type": "string",
            "description": "Name of the entertainment process to monitor (e.g., chrome, vlc, spotify, ffmpeg). Can be a partial match."
        },
        "metrics": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "cpu_percent",
                    "memory_mb",
                    "disk_read_bytes",
                    "disk_write_bytes",
                    "thread_count"
                ]
            },
            "description": "List of system metrics to retrieve for the specified process."
        }
    },
    "required": [
        "media_process_name",
        "metrics"
    ]
},
}
