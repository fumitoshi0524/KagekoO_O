"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Analyze viewership trend data for entertainment shows."""
    import json
    from datetime import datetime, timedelta
    import random
    import math

    try:
        data = json.loads(payload)
        show_title = data.get("show_title")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        granularity = data.get("granularity")
        metric = data.get("metric")

        if not all([show_title, start_date, end_date, granularity, metric]):
            return json.dumps({"error": "Missing required parameters"}, ensure_ascii=False)

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD"}, ensure_ascii=False)

        if start >= end:
            return json.dumps({"error": "start_date must be before end_date"}, ensure_ascii=False)

        # Simulate historical viewership data based on realistic patterns
        viewership_data = []
        current = start
        episode_num = 1

        metric_ranges = {
            "viewers_millions": (0.5, 15.0),
            "rating_score": (1.0, 10.0),
            "share_percentage": (1.0, 40.0)
        }
        metric_min, metric_max = metric_ranges[metric]

        while current <= end:
            # Base value with some randomness
            base = (metric_min + metric_max) / 2

            # Seasonal effect (higher in winter, lower in summer for North America)
            month = current.month
            if 11 <= month <= 2:
                seasonal_factor = 1.2
            elif 6 <= month <= 8:
                seasonal_factor = 0.8
            else:
                seasonal_factor = 1.0

            # Weekend effect (higher viewership on weekends)
            weekday = current.weekday()
            if weekday >= 5:
                weekend_factor = 1.3
            else:
                weekend_factor = 1.0

            # Episode number effect (pilot effect - first episodes higher)
            episode_factor = 1.0 + (0.2 * math.exp(-episode_num / 10))

            # Random fluctuation
            noise = random.uniform(-0.1, 0.1)

            value = base * seasonal_factor * weekend_factor * episode_factor * (1 + noise)
            value = round(max(metric_min, min(metric_max, value)), 2)

            viewership_data.append({
                "date": current.strftime("%Y-%m-%d"),
                "episode": episode_num,
                metric: value
            })

            # Increment based on granularity
            if granularity == "daily":
                current += timedelta(days=1)
                episode_num += 1
            elif granularity == "weekly":
                current += timedelta(weeks=1)
                episode_num += 1
            elif granularity == "monthly":
                current += timedelta(days=30)
                episode_num += 1
            elif granularity == "seasonal":
                current += timedelta(days=91)
                episode_num += 1

        # Calculate trend direction
        if len(viewership_data) >= 2:
            first_value = viewership_data[0][metric]
            last_value = viewership_data[-1][metric]
            if last_value > first_value * 1.05:
                trend = "upward"
            elif last_value < first_value * 0.95:
                trend = "downward"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # Find peak periods
        values = [v[metric] for v in viewership_data]
        if values:
            max_val = max(values)
            peak_indices = [i for i, v in enumerate(values) if v >= max_val * 0.95]
            peak_periods = [viewership_data[i]["date"] for i in peak_indices[:5]]
        else:
            peak_periods = []

        # Calculate retention metrics (between first and second half)
        mid_point = len(viewership_data) // 2
        if mid_point > 0:
            first_half_avg = sum(values[:mid_point]) / mid_point
            second_half = values[mid_point:]
            if second_half:
                second_half_avg = sum(second_half) / len(second_half)
                retention_rate = round((second_half_avg / first_half_avg) * 100, 1) if first_half_avg > 0 else 0
            else:
                retention_rate = 100.0
        else:
            retention_rate = 100.0

        result = {
            "show_title": show_title,
            "analysis_period": f"{start_date} to {end_date}",
            "granularity": granularity,
            "metric_analyzed": metric,
            "trend": trend,
            "total_data_points": len(viewership_data),
            "average_value": round(sum(values) / len(values), 2) if values else 0,
            "peak_value": round(max_val, 2) if values else 0,
            "peak_periods": peak_periods,
            "viewership_data": viewership_data,
            "audience_retention_rate": f"{retention_rate}%"
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Analysis failed: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "viewership_trend_analyzer",
    "description": "Analyze historical TV show or streaming series viewership data to identify weekday vs weekend, seasonal, and episode-number-based rating trends, returning trend direction, peak periods, and audience retention metrics for programming decision support.",
    "category": "analysis",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "show_title": {
            "type": "string",
            "description": "Name of the TV show or streaming series to analyze"
        },
        "start_date": {
            "type": "string",
            "description": "Start date for the analysis window in YYYY-MM-DD format"
        },
        "end_date": {
            "type": "string",
            "description": "End date for the analysis window in YYYY-MM-DD format"
        },
        "granularity": {
            "type": "string",
            "enum": [
                "daily",
                "weekly",
                "monthly",
                "seasonal"
            ],
            "description": "Time granularity for aggregating viewership data"
        },
        "metric": {
            "type": "string",
            "enum": [
                "viewers_millions",
                "rating_score",
                "share_percentage"
            ],
            "description": "Viewership metric to analyze"
        }
    },
    "required": [
        "show_title",
        "start_date",
        "end_date",
        "granularity",
        "metric"
    ]
},
}
