from __future__ import annotations

from .experience_models import (
    ExperienceCapsule,
    ExperienceContext,
    ExperienceFunction,
    ExperienceGovernance,
    ExperienceLinks,
    ExperienceModelProfile,
    ExperienceOutcome,
    ExperienceSolutionTrace,
    ExperienceStep,
    ExperienceTransfer,
    InstinctRef,
    KnowledgeTriple,
    SkillRef,
    ToolCallHint,
)


def upgrade_ecap_v1_to_v2(obj: dict) -> ExperienceCapsule:
    ctx = ExperienceContext(**(obj.get("context") or {}))
    mp_obj = obj.get("model_profile") or {}
    st_obj = obj.get("solution_trace") or {}
    out_obj = obj.get("outcome") or {}
    tr_obj = obj.get("transfer") or {}
    ln_obj = obj.get("links") or {}
    gov_obj = obj.get("governance") or {}

    raw_steps = st_obj.get("steps") or []
    steps: list[ExperienceStep] = []
    for one in raw_steps:
        if isinstance(one, dict):
            steps.append(ExperienceStep(**one))
        else:
            txt = str(one)
            steps.append(
                ExperienceStep(
                    step_type="decision",
                    summary=txt,
                    expected_effect="",
                )
            )

    raw_tools = st_obj.get("tool_sequence") or []
    hints: list[ToolCallHint] = []
    for one in raw_tools:
        if isinstance(one, dict):
            hints.append(ToolCallHint(**one))
        else:
            hints.append(ToolCallHint(tool_name=str(one), count=1, ratio=0.0))

    kt_obj = obj.get("knowledge_triple") or {}
    ir_obj = kt_obj.get("instinct_ref") or {}
    ef_obj = kt_obj.get("experience_fn") or {}
    sr_obj = kt_obj.get("skill_ref") or {}

    cap = ExperienceCapsule(
        schema_version="ecap-v3",
        ecap_id=str(obj.get("ecap_id", "")),
        title=str(obj.get("title", "")),
        problem_type=str(obj.get("problem_type", "general")),
        context=ctx,
        model_profile=ExperienceModelProfile(**mp_obj),
        solution_trace=ExperienceSolutionTrace(
            steps=steps,
            tool_sequence=hints,
            decision_rationale_summary=str(st_obj.get("decision_rationale_summary", "")),
        ),
        outcome=ExperienceOutcome(**out_obj),
        transfer=ExperienceTransfer(**tr_obj),
        links=ExperienceLinks(**ln_obj),
        governance=ExperienceGovernance(**gov_obj),
        knowledge_triple=KnowledgeTriple(
            instinct_ref=InstinctRef(
                instinct_ids=[str(x) for x in (ir_obj.get("instinct_ids") or ln_obj.get("related_instinct_ids") or [])],
                instinct_weights={str(k): float(v) for k, v in (ir_obj.get("instinct_weights") or {}).items()},
                trigger_signature=str(ir_obj.get("trigger_signature") or ""),
            ),
            experience_fn=ExperienceFunction(
                goal=str(ef_obj.get("goal") or ""),
                result=str(ef_obj.get("result") or out_obj.get("result") or ""),
                goal_spec=dict(ef_obj.get("goal_spec") or {}),
                result_spec=dict(ef_obj.get("result_spec") or {}),
                gap=float(ef_obj.get("gap") or 0.0),
                gap_components={str(k): float(v) for k, v in (ef_obj.get("gap_components") or {}).items()},
                gap_vector={str(k): float(v) for k, v in (ef_obj.get("gap_vector") or ef_obj.get("gap_components") or {}).items()},
                fn_type=str(ef_obj.get("fn_type") or "weighted_gap_v1"),
                params={str(k): float(v) for k, v in (ef_obj.get("params") or {}).items()} or ExperienceFunction().params,
                score=float(ef_obj.get("score") or float(gov_obj.get("feedback_score") or 0.0)),
                confidence=float(ef_obj.get("confidence") or 0.5),
                ci_lower=float(ef_obj.get("ci_lower") or 0.0),
                ci_upper=float(ef_obj.get("ci_upper") or 1.0),
                sample_count=int(ef_obj.get("sample_count") or 0),
                learning_rate=float(ef_obj.get("learning_rate") or 0.2),
                decay=float(ef_obj.get("decay") or 0.98),
                effectiveness_level=str(ef_obj.get("effectiveness_level") or "seed"),
                scope=str(ef_obj.get("scope") or "skill"),
                subject_id=str(ef_obj.get("subject_id") or ""),
            ),
            skill_ref=SkillRef(
                skill_name=str(sr_obj.get("skill_name") or ""),
                skill_version=str(sr_obj.get("skill_version") or ""),
                skill_path=str(sr_obj.get("skill_path") or ""),
                invocation_profile=dict(sr_obj.get("invocation_profile") or {}),
            ),
        ),
    )
    if not cap.transfer.model_migration_rules:
        cap.transfer.model_migration_rules = [
            "For weaker target models, split large tasks into smaller verifiable steps.",
            "Increase verification frequency after edits or shell-side effects.",
        ]
    return cap
