"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a time-series CO2 emissions chart as SVG."""
    import json
    try:
        data = json.loads(payload)
        region = data.get("region")
        start_year = data.get("start_year")
        end_year = data.get("end_year")
        source_filter = data.get("source_filter", None)
        chart_style = data.get("chart_style", "stacked_bar")
        title = data.get("title", None)

        if not region or not start_year or not end_year:
            return json.dumps({"error": "Missing required fields: region, start_year, end_year"})
        if not isinstance(start_year, int) or not isinstance(end_year, int):
            return json.dumps({"error": "start_year and end_year must be integers"})
        if start_year < 1850 or end_year > 2025:
            return json.dumps({"error": "Years must be between 1850 and 2025"})
        if start_year > end_year:
            return json.dumps({"error": "start_year must be <= end_year"})

        # Simulated emissions data (tonnes CO2e) for demonstration
        import random
        random.seed(hash(region + str(start_year)) % (2**32))
        categories = ["transportation", "energy", "agriculture", "industrial", "waste"]
        if source_filter:
            for s in source_filter:
                if s not in categories:
                    return json.dumps({"error": f"Invalid source: {s}. Must be one of {categories}"})
            categories = source_filter

        years = list(range(start_year, end_year + 1))
        datasets = {}
        for cat in categories:
            base = random.uniform(100, 1000)
            datasets[cat] = []
            for i, y in enumerate(years):
                noise = random.uniform(-50, 50)
                trend = 5 * i
                datasets[cat].append(max(0, round(base + trend + noise, 2)))

        colors = {
            "transportation": "#FF6B35",
            "energy": "#004E89",
            "agriculture": "#1A936F",
            "industrial": "#C1292E",
            "waste": "#7A5C61"
        }

        # Build SVG bar chart
        width = max(600, len(years) * 60)
        height = 400
        bar_width = min(40, (width - 100) // len(years))
        chart_top = 50
        chart_bottom = height - 50
        chart_height = chart_bottom - chart_top

        max_total = 0
        if chart_style == "stacked_bar":
            for i in range(len(years)):
                total = sum(datasets[cat][i] for cat in categories)
                if total > max_total:
                    max_total = total
        elif chart_style == "grouped_bar":
            for i in range(len(years)):
                for cat in categories:
                    if datasets[cat][i] > max_total:
                        max_total = datasets[cat][i]
        else:
            for i in range(len(years)):
                total = sum(datasets[cat][i] for cat in categories)
                if total > max_total:
                    max_total = total

        max_val = max_total * 1.15

        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        # Background
        svg += f'<rect width="{width}" height="{height}" fill="#f8f9fa" rx="8"/>'
        # Title
        if not title:
            title = f"CO2 Emissions ({', '.join(categories)}) for {region} ({start_year}-{end_year})"
        svg += f'<text x="{width/2}" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">{title}</text>'
        # Y-axis gridlines and labels
        steps = 5
        for s in range(steps + 1):
            y_val = max_val * (steps - s) / steps
            y_pos = chart_top + (chart_height * s / steps)
            svg += f'<line x1="60" y1="{y_pos}" x2="{width-20}" y2="{y_pos}" stroke="#ddd" stroke-width="1"/>'
            svg += f'<text x="55" y="{y_pos+4}" text-anchor="end" font-family="Arial" font-size="10" fill="#666">{y_val:.0f}</text>'
        # X-axis labels
        for i, y in enumerate(years):
            x_pos = 80 + i * ((width - 100) / len(years))
            if len(years) <= 10 or i % max(1, len(years)//10) == 0:
                svg += f'<text x="{x_pos}" y="{chart_bottom+20}" text-anchor="middle" font-family="Arial" font-size="9" fill="#666" transform="rotate(-45, {x_pos}, {chart_bottom+20})">{y}</text>'
        # Data
        if chart_style == "stacked_bar":
            for i in range(len(years)):
                x_pos = 80 + i * ((width - 100) / len(years)) - bar_width/2
                current_top = 0
                for cat in categories:
                    val = datasets[cat][i]
                    bar_h = (val / max_val) * chart_height
                    y_pos = chart_bottom - current_top - bar_h
                    svg += f'<rect x="{x_pos}" y="{y_pos}" width="{bar_width}" height="{bar_h}" fill="{colors[cat]}" opacity="0.85" rx="2">'
                    svg += f'<title>{y} - {cat}: {val} tonnes</title>'
                    svg += '</rect>'
                    current_top += bar_h
        elif chart_style == "grouped_bar":
            group_width = (width - 100) / len(years)
            sub_width = group_width / len(categories) * 0.7
            for i in range(len(years)):
                for j, cat in enumerate(categories):
                    val = datasets[cat][i]
                    bar_h = (val / max_val) * chart_height
                    x_pos = 80 + i * group_width + j * (group_width / len(categories)) + (group_width - sub_width * len(categories)) / 2
                    y_pos = chart_bottom - bar_h
                    svg += f'<rect x="{x_pos}" y="{y_pos}" width="{sub_width}" height="{bar_h}" fill="{colors[cat]}" opacity="0.85" rx="2">'
                    svg += f'<title>{y} - {cat}: {val} tonnes</title>'
                    svg += '</rect>'
        else:  # line chart
            for cat in categories:
                pts = []
                for i in range(len(years)):
                    x_pos = 80 + i * ((width - 100) / len(years))
                    val = datasets[cat][i]
                    y_pos = chart_bottom - (val / max_val) * chart_height
                    pts.append(f"{x_pos},{y_pos}")
                svg += f'<polyline points="{' '.join(pts)}" fill="none" stroke="{colors[cat]}" stroke-width="2.5" opacity="0.8"/>'
                for i in range(len(years)):
                    x_pos = 80 + i * ((width - 100) / len(years))
                    val = datasets[cat][i]
                    y_pos = chart_bottom - (val / max_val) * chart_height
                    svg += f'<circle cx="{x_pos}" cy="{y_pos}" r="3" fill="{colors[cat]}">'
                    svg += f'<title>{years[i]} - {cat}: {val} tonnes</title>'
                    svg += '</circle>'
        # Legend
        legend_x = width - 130
        legend_y = 55
        svg += f'<rect x="{legend_x-5}" y="{legend_y-5}" width="125" height="{len(categories)*20+10}" fill="white" stroke="#ccc" rx="4"/>'
        for j, cat in enumerate(categories):
            svg += f'<rect x="{legend_x}" y="{legend_y+j*20}" width="12" height="12" fill="{colors[cat]}" rx="1"/>'
            svg += f'<text x="{legend_x+18}" y="{legend_y+j*20+11}" font-family="Arial" font-size="10" fill="#333">{cat}</text>'
        svg += '</svg>'

        result = {
            "svg": svg,
            "data": {
                "region": region,
                "years": years,
                "categories": categories,
                "values": datasets
            },
            "metadata": {
                "total_emissions_tonnes": round(sum(sum(datasets[cat]) for cat in categories), 2),
                "year_range": f"{start_year}-{end_year}"
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "carbon_emissions_chart",
    "description": "Generate a time-series bar chart of CO2 equivalent emissions (tonnes) by source category (transportation, energy, agriculture, industrial, waste) for a given geographic region and year range. Returns an HTML SVG string of the chart with interactive tooltips, suitable for embedding in sustainability reports and dashboards.",
    "category": "visualization",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "region": {
            "type": "string",
            "description": "Geographic region or country name (ISO alpha-3 code or common name). Must be a recognized sovereign state or major administrative region.",
            "examples": [
                "DEU",
                "California",
                "EU"
            ]
        },
        "start_year": {
            "type": "integer",
            "description": "Start year for the chart data range (inclusive). Minimum valid year is 1850.",
            "examples": [
                2015
            ]
        },
        "end_year": {
            "type": "integer",
            "description": "End year for the chart data range (inclusive). Must be greater than or equal to start_year and not exceed current year.",
            "examples": [
                2023
            ]
        },
        "source_filter": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "transportation",
                    "energy",
                    "agriculture",
                    "industrial",
                    "waste"
                ]
            },
            "description": "Optional: Filter by specific emission source categories. If omitted, all categories are included.",
            "examples": [
                [
                    "energy",
                    "transportation"
                ]
            ]
        },
        "chart_style": {
            "type": "string",
            "enum": [
                "stacked_bar",
                "grouped_bar",
                "line"
            ],
            "description": "Optional: Visual representation style. Default is stacked_bar.",
            "examples": [
                "grouped_bar"
            ]
        },
        "title": {
            "type": "string",
            "description": "Optional: Custom chart title. If omitted, a descriptive title is auto-generated.",
            "examples": [
                "Germany Energy Sector Emissions 2015-2023"
            ]
        }
    },
    "required": [
        "region",
        "start_year",
        "end_year"
    ]
},
}
