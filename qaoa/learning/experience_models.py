from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


PrivacyLevel = Literal["strict", "balanced", "full"]
ExperienceApplyMode = Literal["concise", "full"]
StepType = Literal["tool_run", "edit", "verify", "decision"]


@dataclass
class ExperienceContext:
    repo_fingerprint: str = ""
    language_stack: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


@dataclass
class ExperienceModelProfile:
    source_provider: str = ""
    source_model: str = ""
    source_model_version: str = ""
    reasoning_effort: str = ""
    tool_budget: int = 0
    capability_profile: dict[str, object] = field(default_factory=dict)


@dataclass
class ToolCallHint:
    tool_name: str = ""
    count: int = 0
    ratio: float = 0.0


@dataclass
class ExperienceStep:
    step_type: StepType = "decision"
    summary: str = ""
    tool_name: str = ""
    params_summary: str = ""
    pre_conditions: list[str] = field(default_factory=list)
    expected_effect: str = ""
    confidence_delta: float = 0.0


@dataclass
class ExperienceSolutionTrace:
    steps: list[ExperienceStep] = field(default_factory=list)
    tool_sequence: list[ToolCallHint] = field(default_factory=list)
    decision_rationale_summary: str = ""


@dataclass
class ExperienceOutcome:
    result: str = "partial"
    verification: list[str] = field(default_factory=list)
    risk_left: list[str] = field(default_factory=list)


@dataclass
class ExperienceTransfer:
    applicability_conditions: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    target_model_hints: list[str] = field(default_factory=list)
    model_migration_rules: list[str] = field(default_factory=list)


@dataclass
class ExperienceLinks:
    related_instinct_ids: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)


@dataclass
class ExperienceGovernance:
    privacy_level: PrivacyLevel = "balanced"
    redaction_applied: bool = True
    reviewed_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    feedback_score: float = 0.0
    feedback_count: int = 0
    deprecated: bool = False


@dataclass
class InstinctRef:
    instinct_ids: list[str] = field(default_factory=list)
    instinct_weights: dict[str, float] = field(default_factory=dict)
    trigger_signature: str = ""


@dataclass
class ExperienceFunction:
    goal: str = ""
    result: str = ""
    goal_spec: dict[str, object] = field(default_factory=dict)
    result_spec: dict[str, object] = field(default_factory=dict)
    gap: float = 0.0
    gap_components: dict[str, float] = field(default_factory=dict)
    gap_vector: dict[str, float] = field(default_factory=dict)
    fn_type: str = "weighted_gap_v1"
    params: dict[str, float] = field(
        default_factory=lambda: {
            "w_quality": 0.4,
            "w_time": 0.2,
            "w_cost": 0.2,
            "w_risk": 0.2,
        }
    )
    score: float = 0.0
    confidence: float = 0.5
    ci_lower: float = 0.0
    ci_upper: float = 1.0
    sample_count: int = 0
    learning_rate: float = 0.2
    decay: float = 0.98
    effectiveness_level: str = "seed"
    scope: str = "skill"
    subject_id: str = ""


@dataclass
class SkillRef:
    skill_name: str = ""
    skill_version: str = ""
    skill_path: str = ""
    invocation_profile: dict[str, object] = field(default_factory=dict)


@dataclass
class KnowledgeTriple:
    instinct_ref: InstinctRef = field(default_factory=InstinctRef)
    experience_fn: ExperienceFunction = field(default_factory=ExperienceFunction)
    skill_ref: SkillRef = field(default_factory=SkillRef)


@dataclass
class ExperienceCapsule:
    schema_version: str = "ecap-v3"
    ecap_id: str = ""
    title: str = ""
    problem_type: str = "general"
    context: ExperienceContext = field(default_factory=ExperienceContext)
    model_profile: ExperienceModelProfile = field(default_factory=ExperienceModelProfile)
    solution_trace: ExperienceSolutionTrace = field(default_factory=ExperienceSolutionTrace)
    outcome: ExperienceOutcome = field(default_factory=ExperienceOutcome)
    transfer: ExperienceTransfer = field(default_factory=ExperienceTransfer)
    links: ExperienceLinks = field(default_factory=ExperienceLinks)
    governance: ExperienceGovernance = field(default_factory=ExperienceGovernance)
    knowledge_triple: KnowledgeTriple = field(default_factory=KnowledgeTriple)
