"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search and retrieve university-level courses by subject, keyword, instructor, or academic level."""
    import json

    # Simulated course database (in production, this would query a real catalog)
    COURSE_CATALOG = [
        {
            "course_code": "CS101",
            "title": "Introduction to Computer Science",
            "credits": 4,
            "description": "Fundamentals of programming, data structures, and algorithms.",
            "instructor": "Dr. Jane Doe",
            "subject": "Computer Science",
            "academic_level": "undergraduate",
            "prerequisites": "None"
        },
        {
            "course_code": "CS201",
            "title": "Data Structures and Algorithms",
            "credits": 4,
            "description": "Advanced data structures and algorithmic problem-solving.",
            "instructor": "Dr. John Smith",
            "subject": "Computer Science",
            "academic_level": "undergraduate",
            "prerequisites": "CS101"
        },
        {
            "course_code": "CS301",
            "title": "Machine Learning",
            "credits": 3,
            "description": "Supervised and unsupervised learning, neural networks, and model evaluation.",
            "instructor": "Dr. Alice Wang",
            "subject": "Computer Science",
            "academic_level": "graduate",
            "prerequisites": "CS201, MATH201"
        },
        {
            "course_code": "MATH101",
            "title": "Calculus I",
            "credits": 4,
            "description": "Limits, derivatives, and integrals of single-variable functions.",
            "instructor": "Dr. Robert Brown",
            "subject": "Mathematics",
            "academic_level": "undergraduate",
            "prerequisites": "High school algebra"
        },
        {
            "course_code": "MATH201",
            "title": "Linear Algebra",
            "credits": 3,
            "description": "Matrices, vector spaces, eigenvalues, and linear transformations.",
            "instructor": "Dr. Emily Davis",
            "subject": "Mathematics",
            "academic_level": "undergraduate",
            "prerequisites": "MATH101"
        },
        {
            "course_code": "PSY101",
            "title": "Introduction to Psychology",
            "credits": 3,
            "description": "Survey of major psychological theories, research methods, and applications.",
            "instructor": "Dr. Sarah Wilson",
            "subject": "Psychology",
            "academic_level": "undergraduate",
            "prerequisites": "None"
        },
        {
            "course_code": "ECON101",
            "title": "Principles of Microeconomics",
            "credits": 3,
            "description": "Supply and demand, market structures, consumer behavior, and firm production.",
            "instructor": "Dr. Michael Lee",
            "subject": "Economics",
            "academic_level": "undergraduate",
            "prerequisites": "None"
        },
        {
            "course_code": "HIST201",
            "title": "World History Since 1500",
            "credits": 3,
            "description": "Global historical developments from the early modern period to the present.",
            "instructor": "Dr. Karen Taylor",
            "subject": "History",
            "academic_level": "undergraduate",
            "prerequisites": "None"
        },
        {
            "course_code": "CS401",
            "title": "Deep Learning",
            "credits": 3,
            "description": "Advanced neural network architectures, CNNs, RNNs, transformers, and applications.",
            "instructor": "Dr. Alice Wang",
            "subject": "Computer Science",
            "academic_level": "graduate",
            "prerequisites": "CS301"
        },
        {
            "course_code": "MATH301",
            "title": "Real Analysis",
            "credits": 4,
            "description": "Rigorous study of real numbers, sequences, continuity, and differentiability.",
            "instructor": "Dr. Robert Brown",
            "subject": "Mathematics",
            "academic_level": "graduate",
            "prerequisites": "MATH201"
        }
    ]

    try:
        data = json.loads(payload)
        subject = data.get("subject")
        keyword = data.get("keyword", "").lower()
        instructor = data.get("instructor", "").lower()
        academic_level = data.get("academic_level", "all").lower()
        max_results = data.get("max_results", 10)

        # Validate required fields
        if not subject:
            return json.dumps({"error": "Missing required parameter: 'subject'"}, ensure_ascii=False)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 50:
            max_results = 10

        # Filter courses
        results = []
        for course in COURSE_CATALOG:
            # Filter by subject (case-insensitive)
            if course["subject"].lower() != subject.lower():
                continue
            # Filter by academic level if specified
            if academic_level != "all" and course["academic_level"].lower() != academic_level:
                continue
            # Filter by keyword (search in title and description)
            if keyword:
                if keyword not in course["title"].lower() and keyword not in course["description"].lower():
                    continue
            # Filter by instructor (full or partial match)
            if instructor:
                if instructor not in course["instructor"].lower():
                    continue
            results.append(course)

        # Limit results
        results = results[:max_results]

        return json.dumps({
            "query": {
                "subject": subject,
                "keyword": keyword if keyword else None,
                "instructor": instructor if instructor else None,
                "academic_level": academic_level,
                "max_results": max_results
            },
            "total_results": len(results),
            "courses": results
        }, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON payload"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "academic_course_finder",
    "description": "Search and retrieve university-level courses by subject, keyword, instructor, or academic level, returning structured course details (title, code, credits, description, prerequisites) for enrollment planning and curriculum exploration.",
    "category": "search",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "subject": {
            "type": "string",
            "description": "Academic subject or discipline to search (e.g., 'Computer Science', 'Mathematics', 'History')",
            "examples": [
                "Computer Science",
                "Psychology",
                "Economics"
            ]
        },
        "keyword": {
            "type": "string",
            "description": "Optional: free-text keyword to further filter courses by title or description (e.g., 'machine learning', 'calculus')",
            "examples": [
                "machine learning",
                "Shakespeare",
                "organic chemistry"
            ]
        },
        "instructor": {
            "type": "string",
            "description": "Optional: instructor name to search for courses taught by a specific professor (e.g., 'Dr. Smith')",
            "examples": [
                "Dr. Jane Doe",
                "Prof. Johnson"
            ]
        },
        "academic_level": {
            "type": "string",
            "enum": [
                "undergraduate",
                "graduate",
                "doctoral",
                "all"
            ],
            "description": "Optional: filter courses by academic level (undergraduate, graduate, doctoral, or all). Default is 'all'.",
            "examples": [
                "undergraduate",
                "graduate"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: maximum number of course listings to return (1 to 50). Default is 10.",
            "minimum": 1,
            "maximum": 50,
            "examples": [
                5,
                10,
                20
            ]
        }
    },
    "required": [
        "subject"
    ]
},
}
