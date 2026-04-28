"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate course progress visualization data for a student."""
    import json
    from datetime import datetime, timedelta
    import random
    
    try:
        data = json.loads(payload)
        student_id = data.get('student_id')
        course_ids = data.get('course_ids', [])
        viz_types = data.get('visualization_types', ['progress_bar', 'completion_pie', 'grade_trend'])
        time_range = data.get('time_range', 'semester')
        
        if not student_id:
            return json.dumps({'error': 'student_id is required'})
        if not course_ids:
            return json.dumps({'error': 'At least one course_id is required'})
        
        valid_viz_types = ['progress_bar', 'completion_pie', 'grade_trend']
        for vt in viz_types:
            if vt not in valid_viz_types:
                return json.dumps({'error': f'Invalid visualization type: {vt}. Must be one of {valid_viz_types}'})
        
        valid_ranges = ['last_30_days', 'semester', 'year']
        if time_range not in valid_ranges:
            return json.dumps({'error': f'Invalid time_range: {time_range}. Must be one of {valid_ranges}'})
        
        result = {
            'student_id': student_id,
            'generated_at': datetime.now().isoformat(),
            'visualizations': {}
        }
        
        for course_id in course_ids:
            result['visualizations'][course_id] = {}
            total_modules = random.randint(5, 15)
            completed_modules = random.randint(0, total_modules)
            completion_pct = round((completed_modules / total_modules) * 100, 1)
            
            if 'progress_bar' in viz_types:
                result['visualizations'][course_id]['progress_bar'] = {
                    'total_modules': total_modules,
                    'completed_modules': completed_modules,
                    'completion_percentage': completion_pct,
                    'label': f'{completed_modules}/{total_modules} modules completed'
                }
            
            if 'completion_pie' in viz_types:
                remaining_modules = total_modules - completed_modules
                result['visualizations'][course_id]['completion_pie'] = {
                    'labels': ['Completed', 'Remaining'],
                    'values': [completed_modules, remaining_modules],
                    'percentage': completion_pct
                }
            
            if 'grade_trend' in viz_types:
                if time_range == 'last_30_days':
                    num_points = 30
                elif time_range == 'semester':
                    num_points = 14
                else:
                    num_points = 52
                
                base_grade = random.uniform(60, 95)
                dates = []
                grades = []
                for i in range(num_points):
                    date = datetime.now() - timedelta(days=num_points - i)
                    dates.append(date.strftime('%Y-%m-%d'))
                    grade = base_grade + random.uniform(-5, 5) + (i * 0.5)
                    grades.append(round(min(max(grade, 0), 100), 1))
                
                result['visualizations'][course_id]['grade_trend'] = {
                    'dates': dates,
                    'grades': grades,
                    'time_range': time_range
                }
        
        return json.dumps(result, ensure_ascii=False, default=str)
    
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "course_progress_visualizer",
    "description": "Generate a visual progress dashboard for a student across multiple courses, showing completion percentages, module status, and grade trends. Returns a JSON structure containing chart data for rendering progress bars, pie charts, and line graphs, used by educators and students to track academic performance.",
    "category": "visualization",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "student_id": {
            "type": "string",
            "description": "Unique identifier for the student"
        },
        "course_ids": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of course identifiers to include in the visualization"
        },
        "visualization_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "progress_bar",
                    "completion_pie",
                    "grade_trend"
                ]
            },
            "description": "Optional: Types of visualizations to generate. Defaults to all three if not specified."
        },
        "time_range": {
            "type": "string",
            "description": "Optional: Time range for trend data (e.g., 'last_30_days', 'semester', 'year'). Defaults to 'semester'."
        }
    },
    "required": [
        "student_id",
        "course_ids"
    ]
},
}
