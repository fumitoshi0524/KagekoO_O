"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    try:
        data = json.loads(payload)
        query = data.get("query", "").strip()
        if not query or len(query) < 3:
            return json.dumps({"error": "Query must be at least 3 characters."}, ensure_ascii=False)
        phase_filter = data.get("trial_phase")
        status_filter = data.get("status")
        max_results = data.get("max_results", 10)
        if not isinstance(max_results, int) or max_results < 1:
            max_results = 10
        if max_results > 50:
            max_results = 50
        # Simulated trial database - in production, query an API like ClinicalTrials.gov
        all_trials = [
            {"nct_id": "NCT04280705", "title": "Study of Remdesivir for COVID-19 Treatment", "phase": "Phase 3", "status": "Completed", "condition": "COVID-19", "location": "United States"},
            {"nct_id": "NCT04425629", "title": "Hydroxychloroquine for Prevention of COVID-19", "phase": "Phase 3", "status": "Completed", "condition": "COVID-19", "location": "Brazil"},
            {"nct_id": "NCT04610528", "title": "Leronlimab for Mild to Moderate COVID-19", "phase": "Phase 2", "status": "Active not recruiting", "condition": "COVID-19", "location": "United States"},
            {"nct_id": "NCT04368728", "title": "mRNA-1273 Vaccine for COVID-19", "phase": "Phase 3", "status": "Completed", "condition": "COVID-19", "location": "United States"},
            {"nct_id": "NCT04583995", "title": "Baricitinib plus Remdesivir for Hospitalized COVID-19", "phase": "Phase 3", "status": "Completed", "condition": "COVID-19", "location": "United States"},
            {"nct_id": "NCT04372082", "title": "Tocilizumab in COVID-19 Pneumonia", "phase": "Phase 3", "status": "Completed", "condition": "COVID-19, Pneumonia", "location": "Italy"},
            {"nct_id": "NCT04381936", "title": "Colchicine for COVID-19", "phase": "Phase 3", "status": "Recruiting", "condition": "COVID-19", "location": "Canada"},
            {"nct_id": "NCT04778393", "title": "Aspirin and Rivaroxaban for Prevention of Thrombosis in COVID-19", "phase": "Phase 2", "status": "Recruiting", "condition": "COVID-19, Thrombosis", "location": "United Kingdom"},
            {"nct_id": "NCT04536792", "title": "Vitamin D and COVID-19 Severity", "phase": "Phase 4", "status": "Active not recruiting", "condition": "COVID-19", "location": "Spain"},
            {"nct_id": "NCT04324463", "title": "Favipiravir for COVID-19", "phase": "Phase 2", "status": "Completed", "condition": "COVID-19", "location": "Japan"},
            {"nct_id": "NCT04445220", "title": "Dexamethasone in Hospitalized COVID-19 Patients", "phase": "Phase 4", "status": "Completed", "condition": "COVID-19", "location": "United Kingdom"},
            {"nct_id": "NCT04649879", "title": "Bamlanivimab for Mild COVID-19", "phase": "Phase 2", "status": "Completed", "condition": "COVID-19", "location": "United States"},
            {"nct_id": "NCT04712669", "title": "Ivermectin for Prevention of COVID-19", "phase": "Phase 3", "status": "Recruiting", "condition": "COVID-19", "location": "India"},
            {"nct_id": "NCT04363450", "title": "Selinexor for Hospitalized COVID-19", "phase": "Phase 2", "status": "Active not recruiting", "condition": "COVID-19", "location": "United States"},
            {"nct_id": "NCT04558476", "title": "N-Acetylcysteine for COVID-19", "phase": "Phase 3", "status": "Recruiting", "condition": "COVID-19", "location": "Iran"}
        ]
        # Filter by query (case-insensitive matching on title, condition, or NCT ID)
        query_lower = query.lower()
        matched = []
        for trial in all_trials:
            if (query_lower in trial["title"].lower() or
                query_lower in trial["condition"].lower() or
                query_lower in trial["nct_id"].lower()):
                matches_phase = True
                if phase_filter:
                    matches_phase = (trial["phase"] == phase_filter)
                matches_status = True
                if status_filter:
                    matches_status = (trial["status"] == status_filter)
                if matches_phase and matches_status:
                    matched.append(trial)
        # Limit results
        matched = matched[:max_results]
        result = {
            "total_matches": len(matched),
            "trials": matched
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "find_clinical_trials",
    "description": "Search for active clinical trials matching a medical condition, drug name, or trial identifier across global registries, returning trial titles, phase, status, location, and enrollment criteria for research and patient referral purposes.",
    "category": "search",
    "domain": "healthcare",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Medical condition, drug name, or trial identifier to search for, at least 3 characters."
        },
        "trial_phase": {
            "type": "string",
            "description": "Optional: Filter by trial phase: Phase 1, Phase 2, Phase 3, Phase 4.",
            "enum": [
                "Phase 1",
                "Phase 2",
                "Phase 3",
                "Phase 4"
            ]
        },
        "status": {
            "type": "string",
            "description": "Optional: Filter by recruitment status: Recruiting, Active not recruiting, Completed, Suspended.",
            "enum": [
                "Recruiting",
                "Active not recruiting",
                "Completed",
                "Suspended"
            ]
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of trials to return (1-50, default 10).",
            "minimum": 1,
            "maximum": 50
        }
    },
    "required": [
        "query"
    ]
},
}
