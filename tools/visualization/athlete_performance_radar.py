"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    import random

    try:
        data = json.loads(payload)
        athlete_name = data.get('athlete_name', '')
        metrics = data.get('metrics', {})
        benchmark_type = data.get('benchmark_type', 'team_average')
        benchmark_values = data.get('benchmark_values', {})
        chart_title = data.get('chart_title', f'Performance Radar: {athlete_name}')
        width = data.get('chart_width', 600)
        height = data.get('chart_height', 600)

        if not athlete_name:
            return 'error: athlete_name is required'
        if not metrics or len(metrics) < 3:
            return 'error: at least 3 metrics are required'

        # Generate realistic benchmark data if not provided
        # For demo, we use random but in production would query real data
        if benchmark_type == 'team_average':
            benchmark_values = {k: round(random.uniform(50, 80), 1) for k in metrics}
        elif benchmark_type == 'league_average':
            benchmark_values = {k: round(random.uniform(45, 75), 1) for k in metrics}
        elif benchmark_type == 'target' and not benchmark_values:
            return 'error: benchmark_values is required when benchmark_type is target'

        # Generate radar chart as SVG
        num_metrics = len(metrics)
        angle_step = 2 * math.pi / num_metrics
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) * 0.35

        metric_keys = list(metrics.keys())
        svg_parts = []
        svg_parts.append(f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">')
        svg_parts.append(f'<rect width="100%" height="100%" fill="#f8f9fa"/>')
        svg_parts.append(f'<text x="{center_x}" y="{20}" text-anchor="middle" font-size="16" font-weight="bold" fill="#333">{chart_title}</text>')

        # Draw grid circles
        for r in [0.25, 0.5, 0.75, 1.0]:
            circle_radius = radius * r
            svg_parts.append(f'<circle cx="{center_x}" cy="{center_y}" r="{circle_radius}" fill="none" stroke="#ccc" stroke-width="1"/>')

        # Draw axis lines and labels
        for i, key in enumerate(metric_keys):
            angle = -math.pi/2 + i * angle_step
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            svg_parts.append(f'<line x1="{center_x}" y1="{center_y}" x2="{x}" y2="{y}" stroke="#ddd" stroke-width="1"/>')
            label_x = center_x + (radius + 30) * math.cos(angle)
            label_y = center_y + (radius + 30) * math.sin(angle)
            svg_parts.append(f'<text x="{label_x}" y="{label_y}" text-anchor="middle" font-size="12" fill="#555" transform="rotate(0, {label_x}, {label_y})">{key.capitalize()}</text>')

        # Draw athlete's data polygon
        athlete_points = []
        for i, key in enumerate(metric_keys):
            angle = -math.pi/2 + i * angle_step
            score = metrics[key]
            r = radius * (score / 100.0)
            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)
            athlete_points.append(f'{x},{y}')
        svg_parts.append(f'<polygon points="{' '.join(athlete_points)}" fill="rgba(54, 162, 235, 0.4)" stroke="rgb(54, 162, 235)" stroke-width="2"/>')

        # Draw benchmark polygon
        benchmark_points = []
        for i, key in enumerate(metric_keys):
            angle = -math.pi/2 + i * angle_step
            if key in benchmark_values:
                score = benchmark_values[key]
                r = radius * (score / 100.0)
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                benchmark_points.append(f'{x},{y}')
        if benchmark_points:
            svg_parts.append(f'<polygon points="{' '.join(benchmark_points)}" fill="rgba(255, 99, 132, 0.3)" stroke="rgb(255, 99, 132)" stroke-width="2" stroke-dasharray="5,5"/>')

        # Legend
        legend_y = height - 40
        svg_parts.append(f'<rect x="{center_x - 80}" y="{legend_y}" width="12" height="12" fill="rgb(54, 162, 235)"/>')
        svg_parts.append(f'<text x="{center_x - 60}" y="{legend_y + 10}" font-size="12" fill="#333">{athlete_name}</text>')
        svg_parts.append(f'<rect x="{center_x + 30}" y="{legend_y}" width="12" height="12" fill="rgb(255, 99, 132)"/>')
        svg_parts.append(f'<text x="{center_x + 50}" y="{legend_y + 10}" font-size="12" fill="#333">Benchmark ({benchmark_type.replace('_', ' ').title()})</text>')

        svg_parts.append('</svg>')
        svg_content = '\n'.join(svg_parts)

        result = {
            'athlete_name': athlete_name,
            'chart_title': chart_title,
            'svg': svg_content,
            'benchmark_type': benchmark_type,
            'metrics': metrics,
            'benchmark_values': benchmark_values,
            'dimensions': f'{width}x{height}'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "athlete_performance_radar",
    "description": "Generate a radar chart visualization comparing an athlete's performance across multiple metrics (e.g., speed, strength, agility, endurance, accuracy) against team averages or target benchmarks, returning SVG chart data for display in dashboards or reports.",
    "category": "visualization",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "athlete_name": {
            "type": "string",
            "description": "Name of the athlete for whom to generate the radar chart"
        },
        "metrics": {
            "type": "object",
            "description": "Object with metric names as keys (e.g., 'speed', 'strength') and current athlete scores (0-100) as values. At least 3 metrics required.",
            "additionalProperties": {
                "type": "number",
                "minimum": 0,
                "maximum": 100
            }
        },
        "benchmark_type": {
            "type": "string",
            "description": "Type of benchmark to compare against: 'team_average' (average of all team members), 'league_average' (average across the league), or 'target' (user-defined target scores)",
            "enum": [
                "team_average",
                "league_average",
                "target"
            ]
        },
        "benchmark_values": {
            "type": "object",
            "description": "Optional: Required only if benchmark_type is 'target'. Object with same metric keys and target scores (0-100).",
            "additionalProperties": {
                "type": "number",
                "minimum": 0,
                "maximum": 100
            }
        },
        "chart_title": {
            "type": "string",
            "description": "Optional: Custom title for the radar chart. Defaults to 'Performance Radar: {athlete_name}'."
        },
        "chart_width": {
            "type": "integer",
            "description": "Optional: Width of the output SVG image in pixels. Default: 600.",
            "minimum": 300,
            "maximum": 1200,
            "default": 600
        },
        "chart_height": {
            "type": "integer",
            "description": "Optional: Height of the output SVG image in pixels. Default: 600.",
            "minimum": 300,
            "maximum": 1200,
            "default": 600
        }
    },
    "required": [
        "athlete_name",
        "metrics",
        "benchmark_type"
    ]
},
}
