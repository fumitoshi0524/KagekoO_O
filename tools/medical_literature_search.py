"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime

    try:
        data = json.loads(payload)
        query = data.get('query')
        max_results = data.get('max_results')
        sort_by = data.get('sort_by')

        if not query or not query.strip():
            return json.dumps({'error': 'query must be a non-empty string'})
        if not isinstance(max_results, int) or max_results < 1 or max_results > 100:
            return json.dumps({'error': 'max_results must be an integer between 1 and 100'})
        if sort_by not in ['relevance', 'date_desc', 'date_asc']:
            return json.dumps({'error': 'sort_by must be one of: relevance, date_desc, date_asc'})

        date_from = data.get('date_from')
        date_to = data.get('date_to')
        if date_from:
            try:
                datetime.strptime(date_from, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'date_from must be in YYYY-MM-DD format'})
        if date_to:
            try:
                datetime.strptime(date_to, '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'date_to must be in YYYY-MM-DD format'})

        article_type = data.get('article_type', 'any')
        if article_type not in ['any', 'clinical_trial', 'review', 'case_report', 'guideline']:
            return json.dumps({'error': 'article_type must be one of: any, clinical_trial, review, case_report, guideline'})

        # Simulated search against a database of medical literature
        simulated_articles = [
            {
                'title': 'Effectiveness of Telemedicine in Managing Type 2 Diabetes: A Meta-Analysis',
                'authors': 'Smith A, Johnson B, Lee C',
                'publication_date': '2024-11-15',
                'abstract': 'A systematic review of 32 randomized controlled trials evaluating telemedicine interventions for glycemic control in type 2 diabetes patients.',
                'type': 'review',
                'relevance_score': 0.95
            },
            {
                'title': 'AI-Assisted Diagnosis of Skin Lesions: A Clinical Trial',
                'authors': 'Patel R, Williams D',
                'publication_date': '2024-09-20',
                'abstract': 'Prospective multicenter clinical trial assessing the accuracy of a deep learning algorithm in detecting malignant melanoma from dermoscopic images.',
                'type': 'clinical_trial',
                'relevance_score': 0.88
            },
            {
                'title': 'Updated Guidelines for Hypertension Management',
                'authors': 'National Heart Institute',
                'publication_date': '2024-07-01',
                'abstract': 'Evidence-based clinical practice guidelines for the prevention, detection, evaluation, and management of high blood pressure in adults.',
                'type': 'guideline',
                'relevance_score': 0.82
            },
            {
                'title': 'Case Report: Unusual Presentation of Lupus Erythematosus',
                'authors': 'Garcia M, Chen X',
                'publication_date': '2024-05-12',
                'abstract': 'A rare case of systemic lupus erythematosus presenting with gastrointestinal symptoms as the initial manifestation.',
                'type': 'case_report',
                'relevance_score': 0.65
            }
        ]

        # Filter by article type
        if article_type != 'any':
            filtered = [a for a in simulated_articles if a['type'] == article_type]
        else:
            filtered = simulated_articles

        # Filter by date range if provided
        if date_from:
            from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            filtered = [a for a in filtered if datetime.strptime(a['publication_date'], '%Y-%m-%d') >= from_dt]
        if date_to:
            to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            filtered = [a for a in filtered if datetime.strptime(a['publication_date'], '%Y-%m-%d') <= to_dt]

        # Sort results
        if sort_by == 'relevance':
            filtered.sort(key=lambda x: x['relevance_score'], reverse=True)
        elif sort_by == 'date_desc':
            filtered.sort(key=lambda x: x['publication_date'], reverse=True)
        elif sort_by == 'date_asc':
            filtered.sort(key=lambda x: x['publication_date'])

        # Apply max_results
        results = filtered[:max_results]

        return json.dumps({'results': results, 'total_found': len(filtered)}, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "medical_literature_search",
    "description": "Search medical literature and clinical guidelines using structured queries against a database of indexed medical articles, returning matching article titles, authors, publication dates, and abstracts for clinical decision support or research reference.",
    "category": "search",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search query for matching medical articles, e.g., disease name, treatment, drug, or condition."
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of search results to return (1-100).",
            "minimum": 1,
            "maximum": 100
        },
        "sort_by": {
            "type": "string",
            "enum": [
                "relevance",
                "date_desc",
                "date_asc"
            ],
            "description": "Sort order for results: by relevance score, newest first, or oldest first."
        },
        "date_from": {
            "type": "string",
            "description": "Optional: Filter articles published on or after this date (ISO 8601 format YYYY-MM-DD).",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
        },
        "date_to": {
            "type": "string",
            "description": "Optional: Filter articles published on or before this date (ISO 8601 format YYYY-MM-DD).",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
        },
        "article_type": {
            "type": "string",
            "enum": [
                "any",
                "clinical_trial",
                "review",
                "case_report",
                "guideline"
            ],
            "description": "Optional: Filter by article type."
        }
    },
    "required": [
        "query",
        "max_results",
        "sort_by"
    ]
},
}
