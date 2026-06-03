"""QAOA module — DLC evolution layer on top of the core learning system.

Pipeline stages (run by Curator every 7-day cycle):
  1. Analytics      — collect stats from trajectories (no LLM)
  2. Evaluate       — LLM decides: which skills → tools? which clusters → MCP?
  3. Promote        — execute decisions (register tool, archive skill, save MCP)

Plus per-session Reflexion: analyze failures → extract lessons → store in Memory.
"""

from kageko.qaoa.tool_generator import ToolGenerator, GeneratedTool
from kageko.qaoa.analytics import AnalyticsEngine, AnalyticsReport, ToolStats, SkillActivity, DomainCluster
from kageko.qaoa.evaluator import Evaluator, PromotionDecision, EvaluationReport
from kageko.qaoa.promoter import Promoter
from kageko.qaoa.reflexion import ReflexionAnalyzer
from kageko.data.qaoa_export import QAOAExporter

__all__ = [
    "ToolGenerator", "GeneratedTool",
    "AnalyticsEngine", "AnalyticsReport", "ToolStats", "SkillActivity", "DomainCluster",
    "Evaluator", "PromotionDecision", "EvaluationReport",
    "Promoter",
    "ReflexionAnalyzer",
    "QAOAExporter",
]
