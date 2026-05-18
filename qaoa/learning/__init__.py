"""Learning and evolution services for qaoa.

Combines ClawCode parity modules with QAOA data pipeline (qaoa_pipeline).
"""

from .qaoa_pipeline import (
    QAOAEvalMetrics, synthesize_qaoa_turns, export_qaoa_jsonl,
    export_qaoa_conversations_jsonl, load_qaoa_jsonl, export_sft_jsonl,
    evaluate_qaoa_predictions, load_toolset_json, export_conversations_jsonl,
    load_conversations_jsonl, evaluate_skill_trajectories,
)
from .service import LearningService
from .store import record_tool_observation
from .experience_models import ExperienceCapsule
from .team_experience_models import TeamExperienceCapsule

# QAOA pipeline exports first
__all__ = [
    "QAOAEvalMetrics", "synthesize_qaoa_turns", "export_qaoa_jsonl",
    "export_qaoa_conversations_jsonl", "load_qaoa_jsonl", "export_sft_jsonl",
    "evaluate_qaoa_predictions", "load_toolset_json", "export_conversations_jsonl",
    "load_conversations_jsonl", "evaluate_skill_trajectories",
    "LearningService", "record_tool_observation", "ExperienceCapsule", "TeamExperienceCapsule",
]
