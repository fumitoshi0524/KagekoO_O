"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a popularity heatmap visualization for entertainment content."""
    import json
    import math
    try:
        data = json.loads(payload)
        content_type = data.get("content_type")
        content_ids = data.get("content_ids", [])
        engagement_metrics = data.get("engagement_metrics", [])
        time_labels = data.get("time_labels", None)
        metric_name = data.get("metric_name", "Engagement")
        color_scheme = data.get("color_scheme", "viridis")

        # Validate required inputs
        if not content_type:
            return json.dumps({"error": "content_type is required"}, ensure_ascii=False)
        if not content_ids or len(content_ids) == 0:
            return json.dumps({"error": "content_ids must be a non-empty list"}, ensure_ascii=False)
        if not engagement_metrics or len(engagement_metrics) == 0:
            return json.dumps({"error": "engagement_metrics must be a non-empty list"}, ensure_ascii=False)

        # Build lookup for engagement data
        metrics_by_id = {}
        for entry in engagement_metrics:
            cid = entry.get("content_id")
            vals = entry.get("metric_values", [])
            if cid:
                metrics_by_id[cid] = vals

        # Ensure all content_ids have data, fill missing with zeros
        max_time_buckets = 0
        for cid in content_ids:
            if cid not in metrics_by_id:
                metrics_by_id[cid] = []
            else:
                max_time_buckets = max(max_time_buckets, len(metrics_by_id[cid]))

        # Normalize all metric arrays to same length
        for cid in content_ids:
            while len(metrics_by_id[cid]) < max_time_buckets:
                metrics_by_id[cid].append(0)

        # Generate time labels if not provided
        if not time_labels or len(time_labels) != max_time_buckets:
            time_labels = [f"Period {i+1}" for i in range(max_time_buckets)]

        # Compute global min/max for normalization
        all_values = []
        for cid in content_ids:
            all_values.extend(metrics_by_id[cid])
        global_min = min(all_values) if all_values else 0
        global_max = max(all_values) if all_values else 1
        if global_max == global_min:
            global_max += 1  # Avoid division by zero

        # Build heatmap grid data
        heatmap_grid = []
        for cid in content_ids:
            row = []
            for val in metrics_by_id[cid]:
                normalized = (val - global_min) / (global_max - global_min)
                intensity = round(normalized * 100)
                row.append({"value": val, "normalized_intensity": intensity})
            heatmap_grid.append({"content_id": cid, "data": row})

        # Compute summary statistics
        content_stats = []
        for cid in content_ids:
            vals = metrics_by_id[cid]
            if vals:
                avg = sum(vals) / len(vals)
                peak = max(vals)
                peak_index = vals.index(peak)
                trend = "up" if len(vals) >= 2 and vals[-1] > vals[0] else ("down" if len(vals) >= 2 and vals[-1] < vals[0] else "stable")
                content_stats.append({
                    "content_id": cid,
                    "average": round(avg, 2),
                    "peak_value": peak,
                    "peak_period": time_labels[peak_index] if time_labels else peak_index,
                    "trend": trend
                })

        # Overall insights
        overall_avg = sum(all_values) / len(all_values) if all_values else 0
        overall_peak = max(all_values) if all_values else 0
        top_content_id = max(content_ids, key=lambda x: metrics_by_id[x][-1] if metrics_by_id[x] else 0) if content_ids else None

        result = {
            "visualization_type": "popularity_heatmap",
            "content_type": content_type,
            "metric_name": metric_name,
            "color_scheme": color_scheme,
            "time_labels": time_labels,
            "heatmap_grid": heatmap_grid,
            "content_statistics": content_stats,
            "summary": {
                "overall_average_engagement": round(overall_avg, 2),
                "overall_peak_engagement": overall_peak,
                "top_content_current_period": top_content_id,
                "content_count": len(content_ids),
                "time_periods": max_time_buckets
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"error: {e}"


TOOL_SPEC = {
    "name": "popularity_heatmap",
    "description": "Generate a popularity heatmap visualization for entertainment content (movies, songs, games, shows) based on provided engagement metrics (views, likes, shares, comments) to identify trending peaks and audience engagement patterns.",
    "category": "visualization",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "content_type": {
            "type": "string",
            "description": "Type of entertainment content to analyze",
            "enum": [
                "movie",
                "song",
                "game",
                "tv_show",
                "podcast"
            ]
        },
        "content_ids": {
            "type": "array",
            "description": "List of content identifiers (titles, track names, or IDs) to include in the heatmap",
            "items": {
                "type": "string"
            }
        },
        "engagement_metrics": {
            "type": "array",
            "description": "Matrix of engagement data: array of objects, each containing content_id and numeric metric values for each time period (e.g., weekly views, daily likes)",
            "items": {
                "type": "object",
                "properties": {
                    "content_id": {
                        "type": "string",
                        "description": "Identifier matching one of the content_ids"
                    },
                    "metric_values": {
                        "type": "array",
                        "description": "Ordered list of numeric engagement values per time bucket (must all be same length)",
                        "items": {
                            "type": "number"
                        }
                    }
                },
                "required": [
                    "content_id",
                    "metric_values"
                ]
            }
        },
        "time_labels": {
            "type": "array",
            "description": "Optional: Labels for each time bucket (e.g., ['Week 1', 'Week 2', ...] or date strings). Defaults to sequential indices if omitted.",
            "items": {
                "type": "string"
            }
        },
        "metric_name": {
            "type": "string",
            "description": "Optional: Human-readable name for the metric being visualized (e.g., 'Weekly Streams', 'Daily Likes'). Defaults to 'Engagement'.",
            "default": "Engagement"
        },
        "color_scheme": {
            "type": "string",
            "description": "Optional: Color gradient scheme for the heatmap. Options: 'viridis', 'plasma', 'coolwarm', 'greens'. Defaults to 'viridis'.",
            "enum": [
                "viridis",
                "plasma",
                "coolwarm",
                "greens"
            ],
            "default": "viridis"
        }
    },
    "required": [
        "content_type",
        "content_ids",
        "engagement_metrics"
    ]
},
}
