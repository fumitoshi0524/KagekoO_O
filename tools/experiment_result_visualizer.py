"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate publication-ready scientific plots from experimental data."""
    import json
    import base64
    import io
    import math
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    try:
        data = json.loads(payload)

        # Validate required fields
        required = ['chart_type', 'x_data', 'y_data', 'x_label', 'y_label']
        for field in required:
            if field not in data:
                return json.dumps({'error': f'Missing required field: {field}'})

        chart_type = data['chart_type']
        x_data = data['x_data']
        y_data = data['y_data']

        # Validate data types and lengths
        if not isinstance(x_data, list) or not isinstance(y_data, list):
            return json.dumps({'error': 'x_data and y_data must be arrays'})
        
        if len(x_data) != len(y_data):
            return json.dumps({'error': f'x_data ({len(x_data)} points) and y_data ({len(y_data)} points) must have the same length'})

        if len(x_data) < 2:
            return json.dumps({'error': 'At least 2 data points are required'})

        # Validate numeric data
        for val in x_data + y_data:
            if not isinstance(val, (int, float)):
                return json.dumps({'error': f'Non-numeric value found: {val}'})
            if math.isnan(val) or math.isinf(val):
                return json.dumps({'error': f'Invalid numeric value (NaN or Inf): {val}'})

        # Parse optional parameters with defaults
        x_label = data['x_label']
        y_label = data['y_label']
        title = data.get('title', '')
        color_scheme = data.get('color_scheme', 'default')
        error_bars = data.get('error_bars', None)
        log_scale_x = data.get('log_scale_x', False)
        log_scale_y = data.get('log_scale_y', False)
        figure_width = min(max(data.get('figure_width', 6.0), 2.0), 12.0)
        figure_height = min(max(data.get('figure_height', 4.5), 2.0), 12.0)
        dpi = min(max(data.get('dpi', 300), 72), 600)

        # Handle negative/no data for log scales
        if log_scale_x and min(x_data) <= 0:
            return json.dumps({'error': 'Cannot use log scale on x-axis with non-positive values'})
        if log_scale_y and min(y_data) <= 0:
            return json.dumps({'error': 'Cannot use log scale on y-axis with non-positive values'})

        # Validate error bars if provided
        if error_bars is not None:
            if not isinstance(error_bars, list):
                return json.dumps({'error': 'error_bars must be an array'})
            if len(error_bars) != len(y_data):
                return json.dumps({'error': f'error_bars ({len(error_bars)} items) must match y_data ({len(y_data)} items) length'})
            for val in error_bars:
                if not isinstance(val, (int, float)) or val < 0:
                    return json.dumps({'error': f'Invalid error bar value (must be non-negative number): {val}'})

        # Validate chart type
        valid_charts = ['line', 'bar', 'scatter', 'histogram', 'box_plot']
        if chart_type not in valid_charts:
            return json.dumps({'error': f'Invalid chart_type: {chart_type}. Must be one of {valid_charts}'})

        # Color scheme configuration
        color_palettes = {
            'default': '#2196F3',
            'colorblind_friendly': '#0072B2',
            'grayscale': '#555555',
            'high_contrast': '#D55E00'
        }
        main_color = color_palettes.get(color_scheme, '#2196F3')

        # Create figure
        fig, ax = plt.subplots(figsize=(figure_width, figure_height))

        # Generate plot based on chart type
        if chart_type == 'line':
            if error_bars:
                ax.errorbar(x_data, y_data, yerr=error_bars, fmt='o-', color=main_color,
                           capsize=3, capthick=1, ecolor='gray', markersize=4)
            else:
                ax.plot(x_data, y_data, 'o-', color=main_color, markersize=4, linewidth=1.5)

        elif chart_type == 'bar':
            x_pos = np.arange(len(x_data))
            if error_bars:
                ax.bar(x_pos, y_data, yerr=error_bars, color=main_color, alpha=0.8,
                       capsize=3, edgecolor='black', linewidth=0.5)
            else:
                ax.bar(x_pos, y_data, color=main_color, alpha=0.8, edgecolor='black', linewidth=0.5)
            ax.set_xticks(x_pos)
            ax.set_xticklabels([f'{v:.2g}' for v in x_data], rotation=45, ha='right')

        elif chart_type == 'scatter':
            ax.scatter(x_data, y_data, c=main_color, alpha=0.7, edgecolors='black', linewidth=0.3)

        elif chart_type == 'histogram':
            ax.hist(x_data, bins='auto', color=main_color, alpha=0.7, edgecolor='black', linewidth=0.5)

        elif chart_type == 'box_plot':
            # For box plot, y_data should be list of groups
            # If single group, wrap it
            if isinstance(y_data[0], list):
                bp = ax.boxplot(y_data, patch_artist=True, widths=0.6)
                for patch in bp['boxes']:
                    patch.set_facecolor(main_color)
                    patch.set_alpha(0.7)
                ax.set_xticklabels([f'{v:.2g}' for v in x_data] if len(x_data) == len(y_data) else [str(i+1) for i in range(len(y_data))], rotation=45, ha='right')
            else:
                bp = ax.boxplot([y_data], patch_artist=True, widths=0.6)
                for patch in bp['boxes']:
                    patch.set_facecolor(main_color)
                    patch.set_alpha(0.7)
                ax.set_xticklabels([x_label])

        # Apply log scales
        if log_scale_x:
            ax.set_xscale('log')
        if log_scale_y:
            ax.set_yscale('log')

        # Labels and formatting
        ax.set_xlabel(x_label, fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=10)

        # Style adjustments for publication quality
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='both', which='major', labelsize=10)
        ax.tick_params(axis='both', which='minor', labelsize=8)

        # Tight layout to avoid label clipping
        plt.tight_layout()

        # Save to buffer as PNG
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)

        # Convert to base64
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        # Return result
        result = {
            'image': img_base64,
            'format': 'png',
            'width_pixels': int(figure_width * dpi),
            'height_pixels': int(figure_height * dpi),
            'dpi': dpi,
            'chart_type': chart_type,
            'data_points': len(x_data),
            'metadata': {
                'x_label': x_label,
                'y_label': y_label,
                'title': title,
                'log_scale_x': log_scale_x,
                'log_scale_y': log_scale_y
            }
        }

        return json.dumps(result, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON input: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Visualization generation failed: {str(e)}'})


TOOL_SPEC = {
    "name": "experiment_result_visualizer",
    "description": "Generate publication-ready scientific plots (line, bar, scatter, histogram, box plot) from experimental data with customizable axis labels, titles, and color schemes. Returns a base64-encoded PNG image of the visualization, suitable for inclusion in research papers, lab notebooks, or presentations.",
    "category": "visualization",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "chart_type": {
            "type": "string",
            "description": "Type of scientific plot to generate",
            "enum": [
                "line",
                "bar",
                "scatter",
                "histogram",
                "box_plot"
            ]
        },
        "x_data": {
            "type": "array",
            "description": "Array of numerical values for the x-axis (independent variable measurements)"
        },
        "y_data": {
            "type": "array",
            "description": "Array of numerical values for the y-axis (dependent variable measurements)"
        },
        "x_label": {
            "type": "string",
            "description": "Label for the x-axis, e.g., 'Time (seconds)' or 'Concentration (mM)'"
        },
        "y_label": {
            "type": "string",
            "description": "Label for the y-axis, e.g., 'Absorbance (OD)' or 'Reaction Rate (μmol/min)'"
        },
        "title": {
            "type": "string",
            "description": "Optional: Title displayed above the chart (e.g., 'Growth Curve of E. coli under Glucose Limitation')"
        },
        "color_scheme": {
            "type": "string",
            "description": "Optional: Color palette for the plot",
            "enum": [
                "default",
                "colorblind_friendly",
                "grayscale",
                "high_contrast"
            ],
            "default": "default"
        },
        "error_bars": {
            "type": "array",
            "description": "Optional: Array of y-error values for error bars (standard deviations or standard errors). Must match length of y_data if provided."
        },
        "log_scale_x": {
            "type": "boolean",
            "description": "Optional: If true, set x-axis to logarithmic scale (common for dose-response curves)",
            "default": false
        },
        "log_scale_y": {
            "type": "boolean",
            "description": "Optional: If true, set y-axis to logarithmic scale (common for growth curves or decay experiments)",
            "default": false
        },
        "figure_width": {
            "type": "number",
            "description": "Optional: Width of the output figure in inches (typical journal requirements: 3.5 for single-column, 7 for double-column)",
            "default": 6.0,
            "minimum": 2.0,
            "maximum": 12.0
        },
        "figure_height": {
            "type": "number",
            "description": "Optional: Height of the output figure in inches",
            "default": 4.5,
            "minimum": 2.0,
            "maximum": 12.0
        },
        "dpi": {
            "type": "integer",
            "description": "Optional: Resolution in dots per inch (300 DPI is standard for publication; 150 for web)",
            "default": 300,
            "minimum": 72,
            "maximum": 600
        }
    },
    "required": [
        "chart_type",
        "x_data",
        "y_data",
        "x_label",
        "y_label"
    ]
},
}
