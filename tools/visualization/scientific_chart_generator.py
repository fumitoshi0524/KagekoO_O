"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        chart_type = data.get('chart_type')
        x_label = data.get('x_label')
        y_label = data.get('y_label')
        data_points = data.get('data_points')
        title = data.get('title', f'{y_label} vs {x_label}')
        series_name = data.get('series_name', 'Experimental Data')
        error_bars = data.get('error_bars', None)

        if not all([chart_type, x_label, y_label, data_points]):
            return json.dumps({'error': 'Missing required parameters: chart_type, x_label, y_label, data_points'})

        if chart_type not in ['scatter', 'line', 'bar']:
            return json.dumps({'error': f'Invalid chart_type: {chart_type}. Must be scatter, line, or bar.'})

        if len(data_points) == 0:
            return json.dumps({'error': 'data_points array must contain at least one point.'})

        # Validate data points
        for i, dp in enumerate(data_points):
            if 'x' not in dp or 'y' not in dp:
                return json.dumps({'error': f'Data point at index {i} missing x or y.'})
            if not isinstance(dp['x'], (int, float)) or not isinstance(dp['y'], (int, float)):
                return json.dumps({'error': f'Data point at index {i} has non-numeric x or y.'})

        if error_bars is not None:
            if len(error_bars) != len(data_points):
                return json.dumps({'error': 'error_bars must have same length as data_points.'})
            for i, eb in enumerate(error_bars):
                if 'y_error' in eb and not isinstance(eb['y_error'], (int, float)):
                    return json.dumps({'error': f'error_bars at index {i} has non-numeric y_error.'})
                if 'x_error' in eb and not isinstance(eb['x_error'], (int, float)):
                    return json.dumps({'error': f'error_bars at index {i} has non-numeric x_error.'})

        # Compute basic statistics for visualization context
        x_values = [dp['x'] for dp in data_points]
        y_values = [dp['y'] for dp in data_points]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)
        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(y_values) / len(y_values)

        # Prepare chart data structure
        chart_data = {
            'type': chart_type,
            'title': title,
            'x_axis': {'label': x_label, 'min': x_min, 'max': x_max},
            'y_axis': {'label': y_label, 'min': y_min, 'max': y_max},
            'series': [
                {
                    'name': series_name,
                    'data': data_points
                }
            ],
            'statistics': {
                'point_count': len(data_points),
                'x_mean': round(x_mean, 6),
                'y_mean': round(y_mean, 6)
            }
        }

        if error_bars is not None:
            chart_data['error_bars'] = error_bars

        return json.dumps(chart_data, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "scientific_chart_generator",
    "description": "Generate a set of chart data from a scientific experiment dataset, producing formatted chart data suitable for creating scatter plots, line graphs, or bar charts representing relationships between experimental variables.",
    "category": "visualization",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "chart_type": {
            "type": "string",
            "enum": [
                "scatter",
                "line",
                "bar"
            ],
            "description": "Type of scientific chart to generate: scatter for correlation, line for trends, bar for comparisons."
        },
        "x_label": {
            "type": "string",
            "description": "Label for the X-axis (e.g., independent variable name, measurement unit)."
        },
        "y_label": {
            "type": "string",
            "description": "Label for the Y-axis (e.g., dependent variable name, measurement unit)."
        },
        "data_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "number",
                        "description": "X-axis value for this data point."
                    },
                    "y": {
                        "type": "number",
                        "description": "Y-axis value for this data point."
                    },
                    "label": {
                        "type": "string",
                        "description": "Optional label for this data point (e.g., experimental condition name)."
                    }
                },
                "required": [
                    "x",
                    "y"
                ]
            },
            "description": "Array of data points, each with x and y coordinates and an optional label."
        },
        "title": {
            "type": "string",
            "description": "Optional: Title of the chart (e.g., 'Temperature vs. Reaction Rate')."
        },
        "series_name": {
            "type": "string",
            "description": "Optional: Name for the data series (used in legends or multi-series charts)."
        },
        "error_bars": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "x_error": {
                        "type": "number",
                        "description": "Optional error value for X-axis (e.g., standard deviation of measurement)."
                    },
                    "y_error": {
                        "type": "number",
                        "description": "Optional error value for Y-axis (e.g., standard error of the mean)."
                    }
                },
                "description": "Optional: Array of error values corresponding to each data point for error bars (only meaningful for scatter/line charts)."
            },
            "description": "Optional: Error bar data for each point (x_error, y_error). Must be same length as data_points if provided."
        }
    },
    "required": [
        "chart_type",
        "x_label",
        "y_label",
        "data_points"
    ]
},
}
