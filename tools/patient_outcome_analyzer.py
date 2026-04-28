"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import statistics
    try:
        data = json.loads(payload)
        records = data.get('patient_records', [])
        if not records:
            return json.dumps({'error': 'patient_records must be a non-empty list'})
        benchmark = data.get('benchmark_data', {})
        
        total = len(records)
        outcomes = [r['outcome'] for r in records]
        los_values = [r['length_of_stay_days'] for r in records]
        complications = [r['has_complication'] for r in records]
        risk_scores = [r['risk_score'] for r in records]
        
        # Recovery rate: recovered or improved
        recovered_count = sum(1 for o in outcomes if o in ['recovered', 'improved'])
        recovery_rate = round(recovered_count / total, 4) if total > 0 else 0
        
        # Complication rate
        complication_count = sum(complications)
        complication_rate = round(complication_count / total, 4) if total > 0 else 0
        
        # Mortality rate
        deceased_count = sum(1 for o in outcomes if o == 'deceased')
        mortality_rate = round(deceased_count / total, 4) if total > 0 else 0
        
        # Length of stay statistics
        avg_los = round(statistics.mean(los_values), 2) if los_values else 0
        median_los = round(statistics.median(los_values), 2) if len(los_values) > 1 else los_values[0] if los_values else 0
        std_los = round(statistics.stdev(los_values), 2) if len(los_values) > 1 else 0
        min_los = min(los_values) if los_values else 0
        max_los = max(los_values) if los_values else 0
        
        # Risk profile
        avg_risk = round(statistics.mean(risk_scores), 2) if risk_scores else 0
        
        # Risk-adjusted recovery rate (simple ratio: observed vs expected based on risk)
        # Expected recovery = average risk score / 100 as proxy
        expected_recovery_based_on_risk = round(sum(r / 100 for r in risk_scores) / total, 4) if total > 0 else 0
        risk_adjusted_recovery_ratio = round(recovery_rate / expected_recovery_based_on_risk, 4) if expected_recovery_based_on_risk > 0 else None
        
        # Department breakdown if available
        departments = {}
        if 'department' in records[0]:
            dept_records = {}
            for r in records:
                dept = r.get('department', 'Unknown')
                if dept not in dept_records:
                    dept_records[dept] = []
                dept_records[dept].append(r)
            for dept, dept_list in dept_records.items():
                dept_total = len(dept_list)
                dept_recovered = sum(1 for o in [d['outcome'] for d in dept_list] if o in ['recovered', 'improved'])
                dept_complications = sum(d['has_complication'] for d in dept_list)
                dept_los = [d['length_of_stay_days'] for d in dept_list]
                departments[dept] = {
                    'patient_count': dept_total,
                    'recovery_rate': round(dept_recovered / dept_total, 4),
                    'complication_rate': round(dept_complications / dept_total, 4),
                    'avg_length_of_stay': round(statistics.mean(dept_los), 2) if dept_los else 0
                }
        
        # Benchmark comparison
        benchmark_comparison = {}
        if benchmark:
            if 'expected_recovery_rate' in benchmark:
                expected_rec = benchmark['expected_recovery_rate']
                benchmark_comparison['recovery_rate_vs_expected'] = round(recovery_rate - expected_rec, 4)
                benchmark_comparison['recovery_rate_ratio'] = round(recovery_rate / expected_rec, 4) if expected_rec > 0 else None
            if 'expected_complication_rate' in benchmark:
                expected_comp = benchmark['expected_complication_rate']
                benchmark_comparison['complication_rate_vs_expected'] = round(complication_rate - expected_comp, 4)
            if 'expected_avg_los' in benchmark:
                expected_los = benchmark['expected_avg_los']
                benchmark_comparison['avg_los_vs_expected'] = round(avg_los - expected_los, 2)
        
        result = {
            'total_patients': total,
            'outcome_summary': {
                'recovery_rate': recovery_rate,
                'mortality_rate': mortality_rate,
                'complication_rate': complication_rate
            },
            'length_of_stay_statistics': {
                'average_days': avg_los,
                'median_days': median_los,
                'standard_deviation_days': std_los,
                'range_days': [min_los, max_los]
            },
            'risk_profile': {
                'average_risk_score': avg_risk,
                'risk_adjusted_recovery_ratio': risk_adjusted_recovery_ratio
            },
            'department_performance': departments if departments else None,
            'benchmark_comparison': benchmark_comparison if benchmark_comparison else None
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)})


TOOL_SPEC = {
    "name": "patient_outcome_analyzer",
    "description": "Analyze patient treatment outcome data to compute recovery rates, complication frequencies, average length of stay, and risk-adjusted performance metrics for a medical department or provider, returning a structured summary for clinical quality improvement and benchmarking.",
    "category": "analysis",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "patient_records": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "outcome": {
                        "type": "string",
                        "enum": [
                            "recovered",
                            "improved",
                            "unchanged",
                            "deteriorated",
                            "deceased"
                        ],
                        "description": "Clinical outcome status at discharge or end of observation period."
                    },
                    "length_of_stay_days": {
                        "type": "number",
                        "description": "Total days the patient was admitted or under active treatment."
                    },
                    "has_complication": {
                        "type": "boolean",
                        "description": "Whether the patient experienced any treatment-related complication."
                    },
                    "risk_score": {
                        "type": "number",
                        "description": "Pre-treatment predicted risk score (0-100) based on comorbidity and severity, used for risk adjustment."
                    },
                    "department": {
                        "type": "string",
                        "description": "Optional: Name of the department or unit providing treatment (e.g., Cardiology, Orthopedics)."
                    }
                },
                "required": [
                    "outcome",
                    "length_of_stay_days",
                    "has_complication",
                    "risk_score"
                ]
            },
            "description": "List of individual patient treatment records to be analyzed collectively."
        },
        "benchmark_data": {
            "type": "object",
            "properties": {
                "expected_recovery_rate": {
                    "type": "number",
                    "description": "Optional: Expected recovery rate (0-1) for the patient population, used for comparison."
                },
                "expected_complication_rate": {
                    "type": "number",
                    "description": "Optional: Expected complication rate (0-1) for the patient population."
                },
                "expected_avg_los": {
                    "type": "number",
                    "description": "Optional: Expected average length of stay in days for the patient population."
                }
            },
            "description": "Optional: External benchmark expectations to compare against observed performance."
        }
    },
    "required": [
        "patient_records"
    ]
},
}
