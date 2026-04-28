"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a comprehensive performance dashboard for one or more athletes across multiple sports metrics."""
    import json
    import math
    import random
    from datetime import datetime, timedelta

    try:
        data = json.loads(payload)
        athlete_ids = data.get('athlete_ids', [])
        metrics = data.get('metrics', [])
        time_period = data.get('time_period', 'last_month')
        comparison_group = data.get('comparison_group', 'none')
        chart_types = data.get('chart_types', None)

        if not athlete_ids:
            return json.dumps({'error': 'At least one athlete ID is required'})
        if not metrics:
            return json.dumps({'error': 'At least one metric is required'})

        valid_metrics = ['speed', 'endurance', 'strength', 'agility', 'accuracy', 'power', 'reaction_time', 'flexibility']
        for m in metrics:
            if m not in valid_metrics:
                return json.dumps({'error': f'Invalid metric: {m}. Must be one of {valid_metrics}'})

        valid_periods = ['last_week', 'last_month', 'last_quarter', 'last_year', 'career']
        if time_period not in valid_periods:
            return json.dumps({'error': f'Invalid time_period: {time_period}. Must be one of {valid_periods}'})

        if comparison_group != 'none' and comparison_group not in ['team', 'league', 'position', 'age_group']:
            return json.dumps({'error': f'Invalid comparison_group: {comparison_group}'})

        period_days = {
            'last_week': 7, 'last_month': 30, 'last_quarter': 90,
            'last_year': 365, 'career': 1825
        }
        num_days = period_days[time_period]

        def generate_performance_data(athlete_id, metric, days):
            random.seed(hash(f'{athlete_id}_{metric}') % (2**31))
            values = []
            for i in range(min(days, 30)):
                base = random.uniform(40, 95)
                trend = (i / 30) * random.uniform(-5, 10)
                noise = random.gauss(0, 5)
                val = round(max(0, min(100, base + trend + noise)), 1)
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                values.append({'date': date, 'value': val})
            values.reverse()
            avg = round(sum(v['value'] for v in values) / len(values), 1)
            max_val = max(v['value'] for v in values)
            min_val = min(v['value'] for v in values)
            trend_direction = 'improving' if values[-1]['value'] > values[0]['value'] else 'declining' if values[-1]['value'] < values[0]['value'] else 'stable'
            std = math.sqrt(sum((v['value'] - avg) ** 2 for v in values) / len(values))
            return {
                'metric': metric,
                'average': avg,
                'max': round(max_val, 1),
                'min': round(min_val, 1),
                'std_dev': round(std, 1),
                'trend': trend_direction,
                'latest': values[-1]['value'],
                'data_points': values
            }

        def generate_comparison_percentile(metric, base_score):
            random.seed(hash(f'comparison_{metric}_{comparison_group}') % (2**31))
            population_mean = random.uniform(45, 75)
            population_std = random.uniform(8, 15)
            z_score = (base_score - population_mean) / population_std
            percentile = round(0.5 * (1 + math.erf(z_score / math.sqrt(2))) * 100, 1)
            return {
                'percentile': min(99.9, max(0.1, percentile)),
                'group_average': round(population_mean, 1),
                'group_size': random.randint(100, 10000)
            }

        dashboard = {
            'title': f'Athlete Performance Dashboard - {time_period.replace("_", " ").title()}',
            'generated_at': datetime.now().isoformat(),
            'athletes': []
        }

        for athlete_id in athlete_ids:
            athlete_data = {'athlete_id': athlete_id, 'name': f'Athlete {athlete_id}', 'metrics': []}
            for metric in metrics:
                perf_data = generate_performance_data(athlete_id, metric, num_days)
                if comparison_group != 'none':
                    perf_data['comparison'] = generate_comparison_percentile(metric, perf_data['average'])
                athlete_data['metrics'].append(perf_data)
            dashboard['athletes'].append(athlete_data)

        chart_suggestions = []
        if chart_types:
            for ct in chart_types:
                if ct in ['radar', 'bar', 'line', 'heatmap', 'scatter', 'trend']:
                    chart_suggestions.append(ct)
        if not chart_suggestions:
            auto_charts = []
            if len(metrics) >= 3:
                auto_charts.append('radar')
            if len(athlete_ids) >= 2:
                auto_charts.append('bar')
            if time_period != 'career':
                auto_charts.append('line')
            if len(metrics) >= 5:
                auto_charts.append('heatmap')
            if len(athlete_ids) >= 2 and len(metrics) >= 2:
                auto_charts.append('scatter')
            chart_suggestions = auto_charts if auto_charts else ['bar']

        dashboard['chart_suggestions'] = chart_suggestions
        dashboard['summary'] = {
            'athlete_count': len(athlete_ids),
            'metric_count': len(metrics),
            'time_period': time_period,
            'top_performers': []
        }

        for metric in metrics:
            best_athlete = max(athlete_ids, key=lambda aid: next(
                m['average'] for a in dashboard['athletes'] if a['athlete_id'] == aid for m in a['metrics'] if m['metric'] == metric
            ))
            best_val = next(m['average'] for a in dashboard['athletes'] if a['athlete_id'] == best_athlete for m in a['metrics'] if m['metric'] == metric)
            dashboard['summary']['top_performers'].append({
                'metric': metric,
                'athlete_id': best_athlete,
                'average_score': best_val
            })

        return json.dumps(dashboard, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': f'Internal error: {str(e)}'})


TOOL_SPEC = {
    "name": "athlete_performance_dashboard",
    "description": "Generate a comprehensive performance dashboard for one or more athletes across multiple sports metrics including speed, endurance, strength, agility, and accuracy, returning a structured JSON visualization bundle with trend summaries, percentile rankings, and comparison charts.",
    "category": "visualization",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "athlete_ids": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "Unique identifier for the athlete (e.g., player ID, jersey number)"
            },
            "description": "List of one or more athlete identifiers to include in the dashboard"
        },
        "metrics": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "speed",
                    "endurance",
                    "strength",
                    "agility",
                    "accuracy",
                    "power",
                    "reaction_time",
                    "flexibility"
                ]
            },
            "description": "Performance metrics to visualize"
        },
        "time_period": {
            "type": "string",
            "enum": [
                "last_week",
                "last_month",
                "last_quarter",
                "last_year",
                "career"
            ],
            "description": "Time period for performance data aggregation"
        },
        "comparison_group": {
            "type": "string",
            "enum": [
                "team",
                "league",
                "position",
                "age_group",
                "none"
            ],
            "description": "Optional: Peer group for percentile ranking comparison"
        },
        "chart_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "radar",
                    "bar",
                    "line",
                    "heatmap",
                    "scatter",
                    "trend"
                ]
            },
            "description": "Optional: Preferred chart types for visualization output. If omitted, best-fit chart type is auto-selected per metric"
        }
    },
    "required": [
        "athlete_ids",
        "metrics",
        "time_period"
    ]
},
}
