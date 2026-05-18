from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PrivacyLevel = Literal["strict", "balanced", "full"]
TeamApplyMode = Literal["concise", "full"]
TeamStepType = Literal["plan", "execute", "review", "handoff", "decision", "escalation"]


@dataclass
class TeamParticipant:
    agent_id: str = ""
    agent_role: str = ""
    model_profile: str = ""
    responsibility: str = ""


@dataclass
class TeamContext:
    objective: str = ""
    constraints: list[str] = field(default_factory=list)
    repo_fingerprint: str = ""
    participants: list[str] = field(default_factory=list)


@dataclass
class TeamToolHint:
    tool_name: str = ""
    count: int = 0


@dataclass
class TeamStep:
    step_id: str = ""
    owner_agent: str = ""
    step_type: TeamStepType = "decision"
    input_summary: str = ""
    output_summary: str = ""
    dependencies: list[str] = field(default_factory=list)
    handoff_to: str = ""
    tool_sequence: list[TeamToolHint] = field(default_factory=list)


@dataclass
class TeamCollaborationTrace:
    steps: list[TeamStep] = field(default_factory=list)


@dataclass
class TeamOutcome:
    result: str = "partial"
    verification: list[str] = field(default_factory=list)
    risk_left: list[str] = field(default_factory=list)
    delivery_metrics: dict[str, object] = field(default_factory=dict)


@dataclass
class TeamTransfer:
    applicability_conditions: list[str] = field(default_factory=list)
    team_migration_hints: list[str] = field(default_factory=list)


@dataclass
class TeamTopology:
    role_graph: list[str] = field(default_factory=list)
    ownership_boundaries: list[str] = field(default_factory=list)
    escalation_chain: list[str] = field(default_factory=list)


@dataclass
class TeamHandoffContract:
    from_role: str = ""
    to_role: str = ""
    input_contract: str = ""
    output_contract: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    sla_hint: str = ""


@dataclass
class TeamDecisionRecord:
    topic: str = ""
    options: list[str] = field(default_factory=list)
    decision: str = ""
    decided_by: str = ""
    confidence: float = 0.0


@dataclass
class TeamCoordinationMetrics:
    handoff_success_rate: float = 0.0
    rework_ratio: float = 0.0
    escalation_count: int = 0
    cycle_time: float = 0.0


@dataclass
class TeamEvidenceRef:
    source_type: str = ""
    source_id: str = ""
    note: str = ""


@dataclass
class TeamIterationRecord:
    iteration: int = 0
    iteration_goal: str = ""
    role_handoff_result: str = ""
    gap_before: float = 0.0
    gap_after: float = 0.0
    gap_delta: float = 0.0
    deviation_reason: str = ""


@dataclass
class TeamExperienceFunction:
    goal: str = ""
    result: str = ""
    goal_spec: dict[str, object] = field(default_factory=dict)
    result_spec: dict[str, object] = field(default_factory=dict)
    gap: float = 0.0
    gap_components: dict[str, float] = field(default_factory=dict)
    gap_vector: dict[str, float] = field(default_factory=dict)
    fn_type: str = "team_weighted_gap_v1"
    params: dict[str, float] = field(
        default_factory=lambda: {
            "w_delivery_quality": 0.35,
            "w_cycle_time": 0.25,
            "w_rework": 0.2,
            "w_escalation": 0.2,
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
    scope: str = "team"
    subject_id: str = ""


@dataclass
class RoleTransferPolicy:
    inheritance_source: str = "same_problem_type"
    confidence_threshold: float = 0.5
    conflict_rule: str = "prefer_high_feedback"


@dataclass
class TeamGovernance:
    privacy_level: PrivacyLevel = "balanced"
    redaction_applied: bool = True
    created_at: str = ""
    updated_at: str = ""
    feedback_score: float = 0.0
    feedback_count: int = 0
    deprecated: bool = False


@dataclass
class TeamExperienceCapsule:
    schema_version: str = "tecap-v3"
    tecap_id: str = ""
    title: str = ""
    problem_type: str = "general"
    team_context: TeamContext = field(default_factory=TeamContext)
    participants: list[TeamParticipant] = field(default_factory=list)
    collaboration_trace: TeamCollaborationTrace = field(default_factory=TeamCollaborationTrace)
    coordination_patterns: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    outcome: TeamOutcome = field(default_factory=TeamOutcome)
    transfer: TeamTransfer = field(default_factory=TeamTransfer)
    team_topology: TeamTopology = field(default_factory=TeamTopology)
    handoff_contracts: list[TeamHandoffContract] = field(default_factory=list)
    decision_log: list[TeamDecisionRecord] = field(default_factory=list)
    coordination_metrics: TeamCoordinationMetrics = field(default_factory=TeamCoordinationMetrics)
    iteration_records: list[TeamIterationRecord] = field(default_factory=list)
    evidence_refs: list[TeamEvidenceRef] = field(default_factory=list)
    quality_gates: list[str] = field(default_factory=list)
    match_explain: list[str] = field(default_factory=list)
    related_ecap_ids: list[str] = field(default_factory=list)
    related_instinct_ids: list[str] = field(default_factory=list)
    role_ecap_map: dict[str, object] = field(default_factory=dict)
    team_experience_fn: TeamExperienceFunction = field(default_factory=TeamExperienceFunction)
    role_transfer_policy: RoleTransferPolicy = field(default_factory=RoleTransferPolicy)
    governance: TeamGovernance = field(default_factory=TeamGovernance)
