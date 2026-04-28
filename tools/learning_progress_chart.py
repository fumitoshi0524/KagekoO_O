"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        student_id = data.get('student_id')
        subjects = data.get('subjects')
        date_range = data.get('date_range')
        chart_type = data.get('chart_type', 'line')
        
        if not student_id or not subjects or not date_range:
            return 'error: Missing required fields'
        
        # Simulate fetching progress data (in production would query an LMS database)
        import random
        progress_data = {}
        for subj in subjects:
            progress_data[subj] = []
            for day in range(31):  # 30 days
                score = random.randint(40, 100)
                progress_data[subj].append({'date': f'2024-01-{day+1:02d}', 'score': score})
        
        # Generate chart (using matplotlib)
        import matplotlib.pyplot as plt
        import base64
        from io import BytesIO
        
        plt.figure(figsize=(10, 6))
        for subj in subjects:
            dates = [entry['date'] for entry in progress_data[subj]]
            scores = [entry['score'] for entry in progress_data[subj]]
            if chart_type == 'line':
                plt.plot(dates, scores, label=subj)
            elif chart_type == 'bar':
                plt.bar(dates, scores, label=subj, alpha=0.6)
            elif chart_type == 'area':
                plt.fill_between(range(len(dates)), scores, label=subj, alpha=0.3)
        
        plt.xlabel('Date')
        plt.ylabel('Score (%)')
        plt.title(f'Learning Progress - {student_id}')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        # Summary statistics
        summary = {}
        for subj in subjects:
            scores = [entry['score'] for entry in progress_data[subj]]
            summary[subj] = {
                'completion_percentage': random.randint(60, 100),
                'average_score': round(sum(scores)/len(scores), 1),
                'max_score': max(scores),
                'min_score': min(scores)
            }
        
        result = {
            'chart_image_base64': img_base64,
            'summary': summary
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "learning_progress_chart",
    "description": "Generate a visual chart showing a student's or cohort's progress over time across multiple subjects or learning modules, returning a base64-encoded PNG image string and a summary of completion percentages and scores.",
    "category": "visualization",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "student_id": {
            "type": "string",
            "description": "Identifier for the student (e.g., 'student_123') or cohort identifier."
        },
        "subjects": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of subject names or module codes to include in the chart (e.g., ['math', 'science'])."
        },
        "date_range": {
            "type": "object",
            "properties": {
                "start": {
                    "type": "string",
                    "format": "date",
                    "description": "Start date in YYYY-MM-DD format."
                },
                "end": {
                    "type": "string",
                    "format": "date",
                    "description": "End date in YYYY-MM-DD format."
                }
            },
            "required": [
                "start",
                "end"
            ],
            "description": "Date range for the progress chart."
        },
        "chart_type": {
            "type": "string",
            "enum": [
                "line",
                "bar",
                "area"
            ],
            "description": "Optional: Type of chart to generate (default 'line'): line, bar, or area."
        }
    },
    "required": [
        "student_id",
        "subjects",
        "date_range"
    ]
},
}
