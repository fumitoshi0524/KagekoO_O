"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a tailored job description based on role parameters."""
    import json
    try:
        data = json.loads(payload)
        title = data.get('role_title', 'Role')
        dept = data.get('department', 'Department')
        skills = data.get('required_skills', [])
        exp = data.get('experience_level', 'mid')
        emp_type = data.get('employment_type', 'full_time')
        location = data.get('location', 'Remote')
        blurb = data.get('company_blurb', 'Our company is a leading innovator in our industry.')
        benefits = data.get('benefits_keywords', ['competitive salary', 'health benefits', 'professional development'])
        salary = data.get('salary_range', '')

        exp_map = {
            'entry': '0-2 years of experience',
            'mid': '3-5 years of experience',
            'senior': '6-9 years of experience',
            'lead': '10+ years of experience',
            'executive': '15+ years of experience with leadership background'
        }
        emp_map = {
            'full_time': 'Full-Time',
            'part_time': 'Part-Time',
            'contract': 'Contract',
            'internship': 'Internship'
        }
        exp_text = exp_map.get(exp, 'Relevant experience')
        emp_text = emp_map.get(emp_type, 'Full-Time')

        skills_formatted = ', '.join(skills) if skills else 'relevant skills'
        benefits_formatted = ', '.join(benefits)

        responsibilities = [
            f'Perform duties as assigned by the {dept} leadership team.',
            f'Apply expertise in {skills_formatted} to drive projects to completion.',
            'Collaborate cross-functionally to align on business objectives.',
            'Mentor junior team members and contribute to team growth.' if exp in ['senior', 'lead', 'executive'] else 'Participate in team meetings and contribute ideas.',
            'Ensure deliverables meet quality standards and deadlines.'
        ]

        qualifications = [
            f'{exp_text} in a related field.',
            f'Proficiency in {skills_formatted}.' if skills else 'Strong analytical and problem-solving skills.',
            'Excellent written and verbal communication skills.',
            'Ability to work independently and in a team environment.'
        ]

        if location and location.lower() != 'remote':
            responsibilities.append(f'Work primarily from {location} according to company policy.')

        result = {
            'job_title': f'{title}',
            'department': dept,
            'employment_type': emp_text,
            'location': location if location else 'Remote',
            'about_us': blurb,
            'responsibilities': responsibilities,
            'qualifications': qualifications,
            'benefits': f'We offer {benefits_formatted}.' if benefits else 'We offer a competitive benefits package.',
            'salary_range': salary if salary else 'Not specified'
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({'error': f'Failed to generate job description: {str(e)}'}, ensure_ascii=False)



TOOL_SPEC = {
    "name": "job_description_generator",
    "description": "Generate a tailored job description based on role title, required skills, and company culture keywords, returning structured sections including responsibilities, qualifications, and benefits for use in recruitment campaigns.",
    "category": "generate",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "role_title": {
            "type": "string",
            "description": "The job title for the position (e.g., 'Senior Software Engineer', 'Marketing Manager')."
        },
        "department": {
            "type": "string",
            "description": "The department name within the company that owns this role (e.g., 'Engineering', 'Marketing')."
        },
        "required_skills": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of key skills or technologies required for the role (e.g., ['Python', 'Project Management', 'SEO'])."
        },
        "experience_level": {
            "type": "string",
            "enum": [
                "entry",
                "mid",
                "senior",
                "lead",
                "executive"
            ],
            "description": "Target experience level for the candidate."
        },
        "employment_type": {
            "type": "string",
            "enum": [
                "full_time",
                "part_time",
                "contract",
                "internship"
            ],
            "description": "Type of employment arrangement."
        },
        "location": {
            "type": "string",
            "description": "Optional: Work location (e.g., 'New York, NY', 'Remote', 'Hybrid - Austin'). Leave empty or omit for fully remote."
        },
        "company_blurb": {
            "type": "string",
            "description": "Optional: Short description of the company mission or culture (e.g., 'We are a fast-growing fintech startup focused on financial inclusion.')."
        },
        "benefits_keywords": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of benefit themes to highlight (e.g., ['unlimited PTO', 'equity', 'health insurance', 'learning budget'])."
        },
        "salary_range": {
            "type": "string",
            "description": "Optional: Salary range text (e.g., '$80,000 - $100,000')."
        }
    },
    "required": [
        "role_title",
        "department",
        "required_skills",
        "experience_level",
        "employment_type"
    ]
},
}
