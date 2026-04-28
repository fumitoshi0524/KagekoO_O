"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    from datetime import datetime, timedelta
    import uuid

    def parse_time(time_str: str) -> tuple:
        try:
            parts = time_str.split(':')
            return int(parts[0]), int(parts[1])
        except:
            raise ValueError(f"Invalid time format: {time_str}")

    try:
        data = json.loads(payload)
        
        # Validate required inputs
        if 'critical_functions' not in data or not isinstance(data['critical_functions'], list):
            return json.dumps({'error': 'critical_functions is required and must be a list'})
        if len(data['critical_functions']) == 0:
            return json.dumps({'error': 'At least one critical function is required'})
        if 'business_hours' not in data:
            return json.dumps({'error': 'business_hours object is required'})
        
        # Extract business hours
        bh = data['business_hours']
        if 'start' not in bh or 'end' not in bh:
            return json.dumps({'error': 'business_hours must include start and end'})
        
        start_h, start_m = parse_time(bh['start'])
        end_h, end_m = parse_time(bh['end'])
        
        # Calculate business hours duration
        business_hours_duration = (end_h * 60 + end_m) - (start_h * 60 + start_m)
        if business_hours_duration <= 0:
            business_hours_duration += 1440  # Add 24 hours in minutes
        
        # Generate plan structure
        plan = {
            'plan_id': str(uuid.uuid4()),
            'generated_at': datetime.now().isoformat(),
            'business_hours': {
                'start': bh['start'],
                'end': bh['end'],
                'timezone': bh.get('timezone', 'UTC'),
                'daily_hours': round(business_hours_duration / 60, 1)
            },
            'critical_functions': [],
            'recovery_strategy': [],
            'alternate_work_sites': [],
            'plan_summary': {}
        }
        
        # Process each critical function
        total_rto = 0
        total_rpo = 0
        
        for func in data['critical_functions']:
            if not isinstance(func, dict):
                continue
                
            function_name = func.get('function_name', 'Unnamed Function')
            max_downtime = func.get('max_downtime_hours', 24)
            max_data_loss = func.get('max_data_loss_minutes', 60)
            dependencies = func.get('dependencies', [])
            
            # Calculate RTO as percentage of business day
            rto = min(max_downtime, business_hours_duration / 60)  # Cap RTO to business day
            rpo = max_data_loss
            
            # Determine priority level based on RTO
            if rto <= 2:
                priority = 'critical'
                response_time = 'immediate'
            elif rto <= 8:
                priority = 'high'
                response_time = 'within 4 hours'
            elif rto <= 48:
                priority = 'medium'
                response_time = 'within 24 hours'
            else:
                priority = 'low'
                response_time = 'within 48 hours'
            
            # Generate action items
            action_items = [
                f"Identify backup personnel for {function_name}",
                f"Document step-by-step recovery procedures for {function_name}",
                f"Test recovery capabilities for {function_name} within {rto} hour(s)"
            ]
            if dependencies:
                for dep in dependencies[:3]:  # Limit to 3
                    action_items.append(f"Establish communication protocol with {dep}")
            
            func_entry = {
                'function_name': function_name,
                'priority': priority,
                'rto_hours': rto,
                'rpo_minutes': rpo,
                'response_time': response_time,
                'dependencies': dependencies,
                'action_items': action_items,
                'recovery_team_required': len(dependencies) > 0
            }
            plan['critical_functions'].append(func_entry)
            
            # Generate recovery strategy
            recovery_step = {
                'function': function_name,
                'strategy': f"Restore {function_name} within {rto} hour(s)",
                'sequence': len(plan['critical_functions']),
                'critical_score': round(rto / (rto + rpo), 2) if rto + rpo > 0 else 0
            }
            plan['recovery_strategy'].append(recovery_step)
            
            total_rto += rto
            total_rpo += rpo
        
        # Process alternate work sites if provided
        if 'alternate_work_sites' in data and isinstance(data['alternate_work_sites'], list):
            for site in data['alternate_work_sites']:
                plan_site = {
                    'site_name': site.get('site_name', 'Unnamed Site'),
                    'capacity': site.get('capacity', 0),
                    'distance_km': site.get('distance_km', 0),
                    'activation_time_hours': 2  # Assumption: 2 hours to activate alternate site
                }
                plan['alternate_work_sites'].append(plan_site)
        
        # Generate plan summary
        total_functions = len(plan['critical_functions'])
        total_actions = sum(len(f['action_items']) for f in plan['critical_functions'])
        avg_rto = round(total_rto / total_functions, 1) if total_functions > 0 else 0
        avg_rpo = round(total_rpo / total_functions, 1) if total_functions > 0 else 0
        
        plan['plan_summary'] = {
            'total_critical_functions': total_functions,
            'total_action_items': total_actions,
            'average_rto_hours': avg_rto,
            'average_rpo_minutes': avg_rpo,
            'total_alternate_sites': len(plan['alternate_work_sites']),
            'overall_preparedness': 'high' if avg_rto <= 4 else 'medium' if avg_rto <= 12 else 'low',
            'document_detail': data.get('document_detail', 'high')
        }
        
        # If high detail requested, add fewer details
        if data.get('document_detail') == 'high':
            # Simplify - keep only minimal info
            for func in plan['critical_functions']:
                del func['action_items']
                del func['dependencies']
                del func['recovery_team_required']
            plan['recovery_strategy'] = []
        
        return json.dumps(plan, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError:
        return json.dumps({'error': 'Invalid JSON payload'})
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'})


TOOL_SPEC = {
    "name": "business_continuity_plan",
    "description": "Generate a business continuity plan document by assessing critical business functions, recovery objectives, and resource requirements, returning a structured JSON plan with recovery time objectives (RTO), recovery point objectives (RPO), and prioritized action items.",
    "category": "system",
    "domain": "business",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "critical_functions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Name of the critical business function"
                    },
                    "max_downtime_hours": {
                        "type": "number",
                        "description": "Maximum tolerable downtime in hours for this function"
                    },
                    "max_data_loss_minutes": {
                        "type": "number",
                        "description": "Maximum acceptable data loss in minutes for this function"
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of dependent systems, personnel, or resources"
                    }
                },
                "required": [
                    "function_name",
                    "max_downtime_hours",
                    "max_data_loss_minutes",
                    "dependencies"
                ]
            },
            "description": "Array of critical business functions with their recovery requirements"
        },
        "business_hours": {
            "type": "object",
            "properties": {
                "start": {
                    "type": "string",
                    "description": "Optional: Business hours start time in HH:MM format (24-hour)"
                },
                "end": {
                    "type": "string",
                    "description": "Optional: Business hours end time in HH:MM format (24-hour)"
                },
                "timezone": {
                    "type": "string",
                    "description": "Optional: IANA timezone identifier (e.g., America/New_York)"
                }
            }
        },
        "alternate_work_sites": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "site_name": {
                        "type": "string",
                        "description": "Name of the alternate work site"
                    },
                    "capacity": {
                        "type": "integer",
                        "description": "Maximum number of people this site can accommodate"
                    },
                    "distance_km": {
                        "type": "number",
                        "description": "Distance from primary location in kilometers"
                    }
                },
                "required": [
                    "site_name",
                    "capacity",
                    "distance_km"
                ]
            },
            "description": "Optional: List of alternate work sites available for relocation"
        },
        "document_detail": {
            "type": "string",
            "enum": [
                "high",
                "full"
            ],
            "description": "Optional: Level of detail for the plan - 'high' for summary, 'full' for comprehensive document"
        }
    },
    "required": [
        "critical_functions",
        "business_hours"
    ]
},
}
