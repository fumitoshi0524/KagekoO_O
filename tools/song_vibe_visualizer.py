"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json, math, base64
    try:
        data = json.loads(payload)
        songs = data['songs']
        chart_type = data['chart_type']
        output_format = data.get('output_format', 'svg')
        if not songs:
            return 'error: songs list cannot be empty'
        for i, s in enumerate(songs):
            if not s.get('title') or not s.get('artist'):
                return f'error: song at index {i} missing title or artist'
            if s.get('danceability') is None:
                s['danceability'] = 0.5
            if s.get('energy') is None:
                s['energy'] = 0.5
            if s.get('valence') is None:
                s['valence'] = 0.5
            for feat in ['danceability', 'energy', 'valence']:
                val = s[feat]
                if not (0 <= val <= 1):
                    return f'error: {feat} must be between 0 and 1 for song {s["title"]}'
        # Compute aggregate mood scores
        n = len(songs)
        avg_dance = sum(s['danceability'] for s in songs) / n
        avg_energy = sum(s['energy'] for s in songs) / n
        avg_valence = sum(s['valence'] for s in songs) / n
        # Classify overall mood
        mood_score = (avg_dance * 0.3 + avg_energy * 0.3 + avg_valence * 0.4)
        if mood_score >= 0.75:
            mood = 'euphoric'
            color = '#FFD700'
        elif mood_score >= 0.5:
            mood = 'upbeat'
            color = '#87CEEB'
        elif mood_score >= 0.25:
            mood = 'melancholic'
            color = '#9B59B6'
        else:
            mood = 'gloomy'
            color = '#34495E'
        if output_format == 'json_data':
            result = {
                'mood': mood,
                'mood_score': round(mood_score, 2),
                'average_features': {
                    'danceability': round(avg_dance, 2),
                    'energy': round(avg_energy, 2),
                    'valence': round(avg_valence, 2)
                },
                'per_song_features': [{'title': s['title'], 'artist': s['artist'], 'danceability': s['danceability'], 'energy': s['energy'], 'valence': s['valence']} for s in songs]
            }
            return json.dumps(result, ensure_ascii=False)
        # Generate SVG
        w, h = 600, 400
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        svg += f'<rect width="{w}" height="{h}" fill="#f8f9fa" rx="10"/>'
        svg += f'<text x="{w/2}" y="30" text-anchor="middle" font-size="20" font-weight="bold" fill="#333">Playlist Mood: {mood.title()}</text>'
        svg += f'<text x="{w/2}" y="55" text-anchor="middle" font-size="14" fill="#666">Score: {round(mood_score,2)}</text>'
        if chart_type == 'radar':
            cx, cy, r = 300, 220, 150
            features = [('Danceability', avg_dance), ('Energy', avg_energy), ('Valence', avg_valence)]
            angles = [0, 360/3, 2*360/3]
            points = []
            for i, (fname, val) in enumerate(features):
                angle_rad = math.radians(angles[i] - 90)
                x = cx + r * val * math.cos(angle_rad)
                y = cy + r * val * math.sin(angle_rad)
                points.append(f'{x},{y}')
                # Axis line
                x_end = cx + r * math.cos(angle_rad)
                y_end = cy + r * math.sin(angle_rad)
                svg += f'<line x1="{cx}" y1="{cy}" x2="{x_end}" y2="{y_end}" stroke="#ccc" stroke-width="1"/>'
                # Label
                lx = cx + (r+30) * math.cos(angle_rad)
                ly = cy + (r+30) * math.sin(angle_rad)
                svg += f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="12" fill="#333">{fname} ({round(val,2)})</text>'
            polygon = ' '.join(points)
            svg += f'<polygon points="{polygon}" fill="{color}" fill-opacity="0.3" stroke="{color}" stroke-width="2"/>'
        elif chart_type == 'bar':
            bar_w = 30
            spacing = 10
            start_x = 60
            y_base = 330
            max_val = max(max(s['danceability'], s['energy'], s['valence']) for s in songs)
            if max_val == 0:
                max_val = 1
            for idx, s in enumerate(songs):
                x = start_x + idx * (bar_w*3 + spacing*2)
                features = [s['danceability'], s['energy'], s['valence']]
                labels = ['D', 'E', 'V']
                colors_bar = ['#FF6384', '#36A2EB', '#FFCE56']
                for j, (val, label, c) in enumerate(zip(features, labels, colors_bar)):
                    bar_h = val / max_val * 250
                    bx = x + j*(bar_w+spacing)
                    svg += f'<rect x="{bx}" y="{y_base-bar_h}" width="{bar_w}" height="{bar_h}" fill="{c}" rx="2"/>'
                    svg += f'<text x="{bx+bar_w/2}" y="{y_base+15}" text-anchor="middle" font-size="10">{label}</text>'
                svg += f'<text x="{x+bar_w*1.5}" y="{y_base+30}" text-anchor="middle" font-size="9" fill="#333">{s["title"][:10]}</text>'
        elif chart_type == 'scatter':
            for idx, s in enumerate(songs):
                x = 80 + s['energy'] * 440
                y = 340 - s['valence'] * 280
                hue = (idx * 137.508) % 360
                svg += f'<circle cx="{x}" cy="{y}" r="6" fill="hsl({hue},70%,50%)" opacity="0.7"/>'
                svg += f'<text x="{x+8}" y="{y+4}" font-size="9" fill="#333">{s["title"][:12]}</text>'
            svg += f'<text x="50" y="30" font-size="12" fill="#666">Energy →</text>'
            svg += f'<text x="10" y="200" font-size="12" fill="#666" transform="rotate(-90,10,200)">Valence →</text>'
        svg += '</svg>'
        result = {
            'mood': mood,
            'mood_score': round(mood_score, 2),
            'chart_type': chart_type,
            'svg': svg
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "song_vibe_visualizer",
    "description": "Analyze a list of song titles and their audio features (danceability, energy, valence) to generate a color-coded radar chart and a summary mood score, helping music curators quickly assess the emotional landscape of a playlist.",
    "category": "visualization",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "songs": {
            "type": "array",
            "description": "Array of song objects, each with a title, artist, and optional audio features (danceability, energy, valence). If features are missing, sensible defaults based on genre will be used.",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Song title"
                    },
                    "artist": {
                        "type": "string",
                        "description": "Artist or band name"
                    },
                    "danceability": {
                        "type": "number",
                        "description": "Optional: Danceability score between 0 and 1 (0=least danceable, 1=most danceable)"
                    },
                    "energy": {
                        "type": "number",
                        "description": "Optional: Energy score between 0 and 1 (0=low energy, 1=high energy)"
                    },
                    "valence": {
                        "type": "number",
                        "description": "Optional: Valence (musical positivity) score between 0 and 1 (0=sad/negative, 1=happy/positive)"
                    }
                },
                "required": [
                    "title",
                    "artist"
                ]
            }
        },
        "chart_type": {
            "type": "string",
            "enum": [
                "radar",
                "bar",
                "scatter"
            ],
            "description": "Type of chart to generate. 'radar' shows overall mood profile, 'bar' compares individual song features, 'scatter' plots valence vs energy."
        },
        "output_format": {
            "type": "string",
            "enum": [
                "svg",
                "json_data"
            ],
            "description": "Optional: Desired output format. 'svg' returns an inline SVG string (default), 'json_data' returns structured data for custom rendering."
        }
    },
    "required": [
        "songs",
        "chart_type"
    ]
},
}
