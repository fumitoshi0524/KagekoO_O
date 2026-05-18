from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

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
# QAOA: build ECAP from QAOA turns
from .models import Instinct


def _infer_problem_type(tool_seq: list[str]) -> str:
    s = " ".join(tool_seq).lower()
    if "test" in s:
        return "test"
    if "diff" in s or "review" in s:
        return "review"
    if "replace" in s or "edit" in s:
        return "refactor"
    if "error" in s or "debug" in s:
        return "debug"
    return "general"


def build_experience_capsule(
    *,
    observations: list[dict[str, Any]],
    instincts: list[Instinct],
    session_id: str = "",
    source_provider: str = "",
    source_model: str = "",
    reasoning_effort: str = "",
    problem_type: str = "",
    skill_name: str = "",
    skill_version: str = "",
    skill_path: str = "",
) -> ExperienceCapsule:
    tool_seq = [str(r.get("tool") or "").strip() for r in observations if str(r.get("tool") or "").strip()]
    top_tools = [k for k, _ in Counter(tool_seq).most_common(6)]
    total_tools = max(1, len(tool_seq))
    inferred_type = problem_type.strip() or _infer_problem_type(tool_seq)
    related = [x.id for x in instincts[:8]]
    now = datetime.now(timezone.utc).isoformat()
    sid = session_id.strip() or "session"
    ecap_id = datetime.now().strftime(f"ecap-{sid}-%Y%m%d-%H%M%S")
    steps: list[ExperienceStep] = []
    for t in top_tools:
        steps.append(
            ExperienceStep(
                step_type="tool_run",
                summary=f"Use `{t}` as part of the problem-solving loop.",
                tool_name=t,
                params_summary="(derived from observations)",
                pre_conditions=["Tool available in current environment."],
                expected_effect="Gather evidence or modify state safely.",
                confidence_delta=0.02,
            )
        )
    if not steps:
        steps = [
            ExperienceStep(
                step_type="decision",
                summary="Collect context first, then iterate with small verifiable changes.",
                expected_effect="Reduce risk of broad regressions.",
            )
        ]
    hints: list[str] = []
    if reasoning_effort.lower() in {"high", "medium"}:
        hints.append("For smaller models, decompose steps and verify each step with tools.")
    if "Shell" in top_tools or "Bash" in top_tools:
        hints.append("Prefer explicit command descriptions and validate outputs before edits.")
    tool_hints: list[ToolCallHint] = []
    cnt = Counter(tool_seq)
    for one, num in cnt.most_common(8):
        tool_hints.append(ToolCallHint(tool_name=one, count=num, ratio=round(num / total_tools, 4)))
    cap_profile = {
        "tool_preference": {x.tool_name: x.ratio for x in tool_hints},
        "available_tool_count": len(cnt),
        "source_session_id": sid,
    }
    instinct_weights = {iid: round(1.0 / max(1, len(related)), 4) for iid in related}
    gap_components = {
        "quality_gap": 0.3 if observations else 0.6,
        "time_gap": 0.4 if observations else 0.6,
        "cost_gap": 0.3 if observations else 0.5,
        "risk_gap": 0.5,
    }
    base_params = ExperienceFunction().params
    gap = (
        base_params["w_quality"] * gap_components["quality_gap"]
        + base_params["w_time"] * gap_components["time_gap"]
        + base_params["w_cost"] * gap_components["cost_gap"]
        + base_params["w_risk"] * gap_components["risk_gap"]
    )
    exp_fn = ExperienceFunction(
        goal=f"Solve {inferred_type} task reliably",
        result="success" if observations else "partial",
        goal_spec={
            "objective": f"solve_{inferred_type}",
            "quality_target": 0.85,
            "time_budget_ratio": 1.0,
            "cost_budget_ratio": 1.0,
            "risk_tolerance": 0.2,
        },
        result_spec={
            "observations_count": len(observations),
            "top_tools": top_tools[:4],
            "result": "success" if observations else "partial",
        },
        gap=round(gap, 4),
        gap_components=gap_components,
        gap_vector=gap_components,
        score=round(max(0.0, min(1.0, 1.0 - gap)), 4),
        confidence=0.55 if observations else 0.4,
        effectiveness_level="seed",
        scope="skill",
        subject_id=skill_name or inferred_type,
    )
    knowledge = KnowledgeTriple(
        instinct_ref=InstinctRef(
            instinct_ids=related,
            instinct_weights=instinct_weights,
            trigger_signature=f"{inferred_type}:{','.join(top_tools[:3])}",
        ),
        experience_fn=exp_fn,
        skill_ref=SkillRef(
            skill_name=skill_name,
            skill_version=skill_version,
            skill_path=skill_path,
            invocation_profile={
                "tool_sequence_top": [x.tool_name for x in tool_hints[:4]],
                "reasoning_effort": reasoning_effort,
                "budget": max(0, len(observations)),
            },
        ),
    )
    return ExperienceCapsule(
        ecap_id=ecap_id,
        title=f"{inferred_type.title()} experience from {sid}",
        problem_type=inferred_type,
        context=ExperienceContext(
            repo_fingerprint=sid,
            language_stack=[],
            constraints=["Avoid unsafe assumptions; verify with tools."],
        ),
        model_profile=ExperienceModelProfile(
            source_provider=source_provider,
            source_model=source_model,
            source_model_version="",
            reasoning_effort=reasoning_effort,
            tool_budget=max(0, len(observations)),
            capability_profile=cap_profile,
        ),
        solution_trace=ExperienceSolutionTrace(
            steps=steps,
            tool_sequence=tool_hints,
            decision_rationale_summary="Summary-only rationale generated from tool usage patterns.",
        ),
        outcome=ExperienceOutcome(
            result="partial" if not observations else "success",
            verification=["Run tests for modified scope."],
            risk_left=["Heuristics may miss hidden dependencies."],
        ),
        transfer=ExperienceTransfer(
            applicability_conditions=["Similar repository layout and tool access."],
            anti_patterns=["Skipping validation after edits."],
            target_model_hints=hints,
            model_migration_rules=[
                "If target model is weaker, split each step and add verification after every tool run.",
                "When tool budget is tight, prioritize read/inspect tools before write tools.",
            ],
        ),
        links=ExperienceLinks(
            related_instinct_ids=related,
            related_files=[],
        ),
        governance=ExperienceGovernance(
            privacy_level="balanced",
            redaction_applied=True,
            reviewed_by="",
            created_at=now,
            updated_at=now,
        ),
        knowledge_triple=knowledge,
    )
