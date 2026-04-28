"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Check the completion status of onboarding tasks for a new employee by department, including HR document submission, IT equipment assignment, security badge activation, and benefits enrollment, returning a structured summary with task-level flags and overall readiness."""
    import json
    try:
        data = json.loads(payload)
        employee_id = data.get('employee_id')
        department = data.get('department')
        check_type = data.get('check_type')
        include_pending = data.get('include_pending_items', False)

        if not employee_id or not department:
            return json.dumps({'error': 'employee_id and department are required'}, ensure_ascii=False)

        # Simulate a real onboarding database lookup
        # In production, this would query an HR/IT system (e.g., Workday, BambooHR, or Jira)
        onboarding_data = {
            'EMP-2025-0123': {
                'Engineering': {
                    'hr_docs': {'status': 'complete', 'submitted_date': '2025-01-15'},
                    'it_setup': {'status': 'complete', 'laptop_assigned': 'MacBook Pro M4', 'peripherals': 'delivered'},
                    'security': {'status': 'pending', 'badge_activation': 'not_started', 'owner': 'Security Team'},
                    'benefits': {'status': 'complete', 'plan_selected': 'PPO Gold', 'enrollment_date': '2025-01-14'}
                },
                'Sales': {
                    'hr_docs': {'status': 'complete', 'submitted_date': '2025-01-10'},
                    'it_setup': {'status': 'pending', 'laptop_assigned': 'Dell XPS', 'peripherals': 'ordered', 'expected_delivery': '2025-01-20'},
                    'security': {'status': 'complete', 'badge_activated': True},
                    'benefits': {'status': 'pending', 'deadline': '2025-01-25', 'owner': 'HR Admin'}
                }
            }
        }

        employee = onboarding_data.get(employee_id, {})
        dept_data = employee.get(department, {})

        if not dept_data:
            return json.dumps({'status': 'not_found', 'message': f'No onboarding record found for {employee_id} in {department}.'}, ensure_ascii=False)

        # Filter by check_type if specified
        if check_type:
            if check_type in dept_data:
                dept_data = {check_type: dept_data[check_type]}
            else:
                return json.dumps({'error': f'Invalid check_type: {check_type}. Valid types: hr_docs, it_setup, security, benefits'}, ensure_ascii=False)

        # Calculate overall readiness
        all_tasks = list(dept_data.values())
        completed_tasks = [t for t in all_tasks if t.get('status') == 'complete']
        overall_ready = len(completed_tasks) == len(all_tasks)

        result = {
            'employee_id': employee_id,
            'department': department,
            'overall_onboarding_ready': overall_ready,
            'total_tasks': len(all_tasks),
            'completed_tasks': len(completed_tasks),
            'task_details': dept_data
        }

        if include_pending:
            pending_items = []
            for category, task in dept_data.items():
                if task.get('status') == 'pending':
                    item = {
                        'category': category,
                        'owner': task.get('owner', 'Unassigned'),
                        'deadline': task.get('deadline', task.get('expected_delivery', 'N/A'))
                    }
                    pending_items.append(item)
            result['pending_items'] = pending_items

        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({'error': f'Failed to process onboarding check: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "employee_onboarding_status",
    "description": "Check the completion status of onboarding tasks for a new employee by department, including HR document submission, IT equipment assignment, security badge activation, and benefits enrollment, returning a structured summary with task-level flags and overall readiness.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "employee_id": {
            "type": "string",
            "description": "Unique identifier for the employee (e.g., 'EMP-2025-0123')"
        },
        "department": {
            "type": "string",
            "description": "Department name for contextual onboarding workflow (e.g., 'Engineering', 'Sales')",
            "enum": [
                "Engineering",
                "Sales",
                "Marketing",
                "HR",
                "Finance",
                "Operations"
            ]
        },
        "check_type": {
            "type": "string",
            "description": "Optional: Onboarding category to filter results. If omitted, all tasks are returned.",
            "enum": [
                "hr_docs",
                "it_setup",
                "security",
                "benefits"
            ]
        },
        "include_pending_items": {
            "type": "boolean",
            "description": "Optional: If True, include pending/overdue tasks with their assigned owners and deadlines.",
            "default": False
        }
    },
    "required": [
        "employee_id",
        "department"
    ]
},
}
