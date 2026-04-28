"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        courses = data.get("courses")
        if not courses or not isinstance(courses, list):
            return "error: 'courses' must be a non-empty list of strings"
        student_level = data.get("student_level", "undergraduate")
        if student_level not in ["undergraduate", "graduate", "phd"]:
            return "error: invalid student_level, must be one of undergraduate, graduate, phd"
        
        # Simulated difficulty analysis logic based on course name heuristics
        difficulty_results = []
        for course in courses:
            course_lower = course.lower()
            # Estimate difficulty based on keywords
            if any(kw in course_lower for kw in ["advanced", "complex", "theory", "research", "seminar"]):
                difficulty = "high"
                workload = "15-20 hours/week"
                pass_rate = 0.72
            elif any(kw in course_lower for kw in ["introduction", "foundations", "basics", "101", "fundamentals"]):
                difficulty = "low"
                workload = "5-10 hours/week"
                pass_rate = 0.88
            else:
                difficulty = "medium"
                workload = "10-15 hours/week"
                pass_rate = 0.81
            
            # Adjust for student level
            if student_level == "graduate" and difficulty == "low":
                difficulty = "medium"
                workload = "8-12 hours/week"
                pass_rate = 0.82
            elif student_level == "phd" and difficulty in ["low", "medium"]:
                difficulty = "high"
                workload = "12-20 hours/week"
                pass_rate = 0.75
            
            difficulty_results.append({
                "course": course,
                "estimated_difficulty": difficulty,
                "estimated_workload": workload,
                "historical_pass_rate": pass_rate,
                "prerequisite_complexity": "moderate" if difficulty == "medium" else ("high" if difficulty == "high" else "low")
            })
        
        result = {
            "student_level": student_level,
            "courses_analyzed": len(courses),
            "difficulty_breakdown": {
                "low": sum(1 for d in difficulty_results if d["estimated_difficulty"] == "low"),
                "medium": sum(1 for d in difficulty_results if d["estimated_difficulty"] == "medium"),
                "high": sum(1 for d in difficulty_results if d["estimated_difficulty"] == "high")
            },
            "analysis": difficulty_results
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "course_difficulty_analyzer",
    "description": "Analyze a list of course codes or course names and return estimated difficulty levels based on historical pass rates, workload hours, and prerequisite complexity within an academic program, used for academic planning and workload balancing.",
    "category": "analysis",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "courses": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of course identifiers (e.g., course codes or names) to analyze. Each should be a non-empty string representing a valid course in the system."
        },
        "student_level": {
            "type": "string",
            "enum": [
                "undergraduate",
                "graduate",
                "phd"
            ],
            "description": "Optional: Academic level of the student or target audience. Defaults to 'undergraduate' if not provided."
        }
    },
    "required": [
        "courses"
    ]
},
}
