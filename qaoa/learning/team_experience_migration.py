from __future__ import annotations

from .team_experience_models import (
    RoleTransferPolicy,
    TeamCollaborationTrace,
    TeamContext,
    TeamCoordinationMetrics,
    TeamDecisionRecord,
    TeamEvidenceRef,
    TeamIterationRecord,
    TeamExperienceFunction,
    TeamExperienceCapsule,
    TeamGovernance,
    TeamHandoffContract,
    TeamOutcome,
    TeamParticipant,
    TeamStep,
    TeamToolHint,
    TeamTopology,
    TeamTransfer,
)


def upgrade_tecap_v1_to_v2(obj: dict) -> TeamExperienceCapsule:
    team_context = TeamContext(**(obj.get("team_context") or {}))
    participants = [TeamParticipant(**x) for x in (obj.get("participants") or []) if isinstance(x, dict)]

    steps: list[TeamStep] = []
    raw_steps = ((obj.get("collaboration_trace") or {}).get("steps") or [])
    for idx, one in enumerate(raw_steps, 1):
        if isinstance(one, dict):
            tool_seq = [TeamToolHint(**t) for t in (one.get("tool_sequence") or []) if isinstance(t, dict)]
            data = dict(one)
            data["tool_sequence"] = tool_seq
            if not data.get("step_id"):
                data["step_id"] = f"s{idx}"
            steps.append(TeamStep(**data))

    topology = TeamTopology(**(obj.get("team_topology") or {}))
    handoff_contracts = [
        TeamHandoffContract(**x) for x in (obj.get("handoff_contracts") or []) if isinstance(x, dict)
    ]
    decision_log = [TeamDecisionRecord(**x) for x in (obj.get("decision_log") or []) if isinstance(x, dict)]
    evidence_refs = [TeamEvidenceRef(**x) for x in (obj.get("evidence_refs") or []) if isinstance(x, dict)]
    metrics = TeamCoordinationMetrics(**(obj.get("coordination_metrics") or {}))
    iteration_records = [TeamIterationRecord(**x) for x in (obj.get("iteration_records") or []) if isinstance(x, dict)]
    match_explain = [str(x) for x in (obj.get("match_explain") or [])]

    raw_role_map = obj.get("role_ecap_map") or {}
    role_ecap_map: dict[str, object] = {}
    for k, v in raw_role_map.items():
        key = str(k)
        if isinstance(v, str):
            role_ecap_map[key] = {"mode": "reference", "ecap_id": v}
        elif isinstance(v, dict):
            role_ecap_map[key] = v
        else:
            role_ecap_map[key] = {"mode": "reference", "ecap_id": ""}
    tef_obj = obj.get("team_experience_fn") or {}
    rtp_obj = obj.get("role_transfer_policy") or {}

    cap = TeamExperienceCapsule(
        schema_version="tecap-v3",
        tecap_id=str(obj.get("tecap_id", "")),
        title=str(obj.get("title", "")),
        problem_type=str(obj.get("problem_type", "general")),
        team_context=team_context,
        participants=participants,
        collaboration_trace=TeamCollaborationTrace(steps=steps),
        coordination_patterns=[str(x) for x in (obj.get("coordination_patterns") or [])],
        anti_patterns=[str(x) for x in (obj.get("anti_patterns") or [])],
        outcome=TeamOutcome(**(obj.get("outcome") or {})),
        transfer=TeamTransfer(**(obj.get("transfer") or {})),
        team_topology=topology,
        handoff_contracts=handoff_contracts,
        decision_log=decision_log,
        coordination_metrics=metrics,
        iteration_records=iteration_records,
        evidence_refs=evidence_refs,
        quality_gates=[str(x) for x in (obj.get("quality_gates") or [])],
        match_explain=match_explain,
        related_ecap_ids=[str(x) for x in (obj.get("related_ecap_ids") or [])],
        related_instinct_ids=[str(x) for x in (obj.get("related_instinct_ids") or [])],
        role_ecap_map=role_ecap_map,
        team_experience_fn=TeamExperienceFunction(
            goal=str(tef_obj.get("goal") or ""),
            result=str(tef_obj.get("result") or (obj.get("outcome") or {}).get("result") or ""),
            goal_spec=dict(tef_obj.get("goal_spec") or {}),
            result_spec=dict(tef_obj.get("result_spec") or {}),
            gap=float(tef_obj.get("gap") or 0.0),
            gap_components={str(k): float(v) for k, v in (tef_obj.get("gap_components") or {}).items()},
            gap_vector={str(k): float(v) for k, v in (tef_obj.get("gap_vector") or tef_obj.get("gap_components") or {}).items()},
            fn_type=str(tef_obj.get("fn_type") or "team_weighted_gap_v1"),
            params={str(k): float(v) for k, v in (tef_obj.get("params") or {}).items()} or TeamExperienceFunction().params,
            score=float(tef_obj.get("score") or float((obj.get("governance") or {}).get("feedback_score") or 0.0)),
            confidence=float(tef_obj.get("confidence") or 0.5),
            ci_lower=float(tef_obj.get("ci_lower") or 0.0),
            ci_upper=float(tef_obj.get("ci_upper") or 1.0),
            sample_count=int(tef_obj.get("sample_count") or 0),
            learning_rate=float(tef_obj.get("learning_rate") or 0.2),
            decay=float(tef_obj.get("decay") or 0.98),
            effectiveness_level=str(tef_obj.get("effectiveness_level") or "seed"),
            scope=str(tef_obj.get("scope") or "team"),
            subject_id=str(tef_obj.get("subject_id") or ""),
        ),
        role_transfer_policy=RoleTransferPolicy(
            inheritance_source=str(rtp_obj.get("inheritance_source") or "same_problem_type"),
            confidence_threshold=float(rtp_obj.get("confidence_threshold") or 0.5),
            conflict_rule=str(rtp_obj.get("conflict_rule") or "prefer_high_feedback"),
        ),
        governance=TeamGovernance(**(obj.get("governance") or {})),
    )

    if not cap.team_topology.role_graph:
        roles = [p.agent_role or p.agent_id for p in cap.participants if (p.agent_role or p.agent_id)]
        cap.team_topology.role_graph = [f"{a}->{b}" for a, b in zip(roles, roles[1:], strict=False)]
    if not cap.quality_gates:
        cap.quality_gates = [
            "Each handoff includes explicit acceptance criteria.",
            "At least one independent review step exists in collaboration trace.",
            "Escalation path is defined for blocked dependencies.",
        ]
    return cap
