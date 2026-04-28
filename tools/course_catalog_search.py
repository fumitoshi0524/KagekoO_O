"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search across an educational course catalog by keyword, subject area, level, and delivery format to find matching courses with their descriptions, prerequisites, and credit values."""
    import json
    try:
        data = json.loads(payload)
        query = data.get("query", "").strip()
        if not query:
            return json.dumps({"error": "Query parameter is required"}, ensure_ascii=False)
        subject_area = data.get("subject_area", "").strip().lower()
        level = data.get("level", "all").strip().lower()
        delivery_format = data.get("delivery_format", "all").strip().lower()
        max_results = min(data.get("max_results", 20), 100)
        if max_results < 1:
            max_results = 20

        # Simulated course catalog database
        catalog = [
            {"id": "CS101", "title": "Introduction to Computer Science", "description": "Fundamentals of programming, algorithms, and data structures using Python.", "subject": "computer science", "level": "undergraduate", "format": "in_person", "credits": 4, "prerequisites": []},
            {"id": "CS201", "title": "Data Structures and Algorithms", "description": "Advanced data structures, algorithm design and analysis.", "subject": "computer science", "level": "undergraduate", "format": "in_person", "credits": 4, "prerequisites": ["CS101"]},
            {"id": "MATH101", "title": "Calculus I", "description": "Limits, derivatives, integrals, and the Fundamental Theorem of Calculus.", "subject": "mathematics", "level": "undergraduate", "format": "hybrid", "credits": 4, "prerequisites": []},
            {"id": "MATH201", "title": "Linear Algebra", "description": "Vector spaces, matrices, determinants, eigenvalues and eigenvectors.", "subject": "mathematics", "level": "undergraduate", "format": "in_person", "credits": 3, "prerequisites": ["MATH101"]},
            {"id": "BIO101", "title": "Principles of Biology", "description": "Cell biology, genetics, evolution, and ecology.", "subject": "biology", "level": "undergraduate", "format": "online_asynchronous", "credits": 4, "prerequisites": []},
            {"id": "HIST101", "title": "World History to 1500", "description": "Survey of world civilizations from prehistory to 1500 CE.", "subject": "history", "level": "undergraduate", "format": "in_person", "credits": 3, "prerequisites": []},
            {"id": "CS601", "title": "Machine Learning", "description": "Supervised and unsupervised learning, neural networks, and model evaluation.", "subject": "computer science", "level": "graduate", "format": "online_synchronous", "credits": 3, "prerequisites": ["CS201", "MATH201"]},
            {"id": "MATH601", "title": "Advanced Calculus", "description": "Rigorous treatment of real analysis, sequences, series, and metric spaces.", "subject": "mathematics", "level": "graduate", "format": "in_person", "credits": 3, "prerequisites": ["MATH201"]},
            {"id": "EDU101", "title": "Teaching with Technology", "description": "Integrating digital tools and online resources into classroom instruction.", "subject": "education", "level": "professional_development", "format": "online_asynchronous", "credits": 2, "prerequisites": []},
            {"id": "MGMT201", "title": "Project Management Fundamentals", "description": "Agile and traditional project management methodologies for professionals.", "subject": "business", "level": "continuing_education", "format": "hybrid", "credits": 3, "prerequisites": []}
        ]

        # Filter by query (keyword search on title and description)
        query_lower = query.lower()
        results = [c for c in catalog if query_lower in c["title"].lower() or query_lower in c["description"].lower()]

        # Filter by subject area
        if subject_area:
            results = [c for c in results if c["subject"] == subject_area]

        # Filter by level
        if level != "all":
            results = [c for c in results if c["level"] == level]

        # Filter by delivery format
        if delivery_format != "all":
            results = [c for c in results if c["format"] == delivery_format]

        # Limit results
        results = results[:max_results]

        return json.dumps({"results": results, "count": len(results)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "course_catalog_search",
    "description": "Search across an educational course catalog by keyword, subject area, level, and delivery format to find matching courses with their descriptions, prerequisites, and credit values.",
    "category": "search",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Keywords or phrase to search for in course titles and descriptions"
        },
        "subject_area": {
            "type": "string",
            "description": "Optional: Filter results to a specific academic subject area (e.g., Mathematics, Computer Science, History, Biology)"
        },
        "level": {
            "type": "string",
            "description": "Optional: Filter by educational level",
            "enum": [
                "undergraduate",
                "graduate",
                "continuing_education",
                "professional_development",
                "all"
            ]
        },
        "delivery_format": {
            "type": "string",
            "description": "Optional: Filter by course delivery method",
            "enum": [
                "in_person",
                "online_synchronous",
                "online_asynchronous",
                "hybrid",
                "all"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of results to return (1-100)",
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": [
        "query"
    ]
},
}
