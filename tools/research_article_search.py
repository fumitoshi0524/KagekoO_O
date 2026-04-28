"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get('query')
        if not query:
            return json.dumps({'error': 'Missing required parameter: query'}, ensure_ascii=False)
        author = data.get('author')
        doi = data.get('doi')
        pub_year_from = data.get('publication_year_from')
        pub_year_to = data.get('publication_year_to')
        max_results = data.get('max_results', 10)
        if max_results < 1 or max_results > 50:
            max_results = 10
        sort_by = data.get('sort_by', 'relevance')
        if sort_by not in ['relevance', 'publication_date_desc', 'publication_date_asc', 'citations_desc']:
            sort_by = 'relevance'
        # Simulated search against an internal database of 1000+ sci articles
        articles = []
        # In a real implementation, this would query a full-text search index
        # For demonstration, generate synthetic results based on query matching
        import datetime
        sample_authors = ['Smith, J.', 'Johnson, L.', 'Williams, R.', 'Brown, A.', 'Davis, M.', 'Miller, K.', 'Wilson, T.', 'Moore, S.', 'Taylor, P.', 'Anderson, E.']
        sample_journals = ['Nature', 'Science', 'Cell', 'PNAS', 'The Lancet', 'Physical Review Letters', 'Journal of the American Chemical Society', 'Neuron', 'The Astrophysical Journal', 'Geophysical Research Letters']
        sample_dois = ['10.1038/s41586-023-05890-5', '10.1126/science.ade580', '10.1016/j.cell.2022.11.001', '10.1073/pnas.2123456119']
        sample_keywords = ['machine learning', 'climate change', 'genomics', 'quantum computing', 'neuroscience', 'cancer research', 'dark matter', 'protein folding', 'biodiversity', 'renewable energy']
        for i in range(min(max_results, 20)):
            year = 2015 + (i % 10)
            if pub_year_from and year < pub_year_from:
                year = pub_year_from
            if pub_year_to and year > pub_year_to:
                year = pub_year_to
            citations = (2025 - year) * 10 + i * 5
            article = {
                'title': f'{query.capitalize()} in {sample_keywords[i % len(sample_keywords)]}: A Comprehensive Study (Part {i+1})',
                'authors': ', '.join(sample_authors[i:i+3]),
                'journal': sample_journals[i % len(sample_journals)],
                'publication_year': year,
                'doi': sample_dois[i % len(sample_dois)],
                'abstract_preview': f'This study investigates the role of {query} in {sample_keywords[i % len(sample_keywords)]}, revealing significant insights into underlying mechanisms and potential applications.',
                'citations': citations
            }
            if author and author.lower() not in article['authors'].lower():
                continue
            if doi and doi != article['doi']:
                continue
            articles.append(article)
        if sort_by == 'publication_date_desc':
            articles.sort(key=lambda x: x['publication_year'], reverse=True)
        elif sort_by == 'publication_date_asc':
            articles.sort(key=lambda x: x['publication_year'])
        elif sort_by == 'citations_desc':
            articles.sort(key=lambda x: x['citations'], reverse=True)
        result = {
            'total_results': len(articles),
            'query': query,
            'articles': articles[:max_results]
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Internal error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "research_article_search",
    "description": "Search across a curated database of scientific research articles by title, author, keywords, DOI, or publication year, returning matching articles with their metadata including authors, journal, publication date, abstract snippet, and citation count.",
    "category": "search",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Free-text search query for matching against article titles, abstracts, and keywords"
        },
        "author": {
            "type": "string",
            "description": "Optional: Full or partial author name to filter results"
        },
        "doi": {
            "type": "string",
            "description": "Optional: Digital Object Identifier for exact article lookup"
        },
        "publication_year_from": {
            "type": "integer",
            "description": "Optional: Minimum publication year (inclusive) for filtering results, e.g. 2018",
            "minimum": 1900,
            "maximum": 2026
        },
        "publication_year_to": {
            "type": "integer",
            "description": "Optional: Maximum publication year (inclusive) for filtering results, e.g. 2024",
            "minimum": 1900,
            "maximum": 2026
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (default 10, max 50)",
            "minimum": 1,
            "maximum": 50,
            "default": 10
        },
        "sort_by": {
            "type": "string",
            "description": "Optional: Sort order for results",
            "enum": [
                "relevance",
                "publication_date_desc",
                "publication_date_asc",
                "citations_desc"
            ],
            "default": "relevance"
        }
    },
    "required": [
        "query"
    ]
},
}
