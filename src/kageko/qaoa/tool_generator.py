"""QAOA Tool Generator — thin facade over the full promotion pipeline.

Delegates to: AnalyticsEngine → Evaluator → Promoter
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB
    from kageko.tools.registry import ToolRegistry

logger = logging.getLogger("kageko.qaoa")


@dataclass
class GeneratedTool:
    name: str
    category: str
    description: str
    parameters: dict
    implementation: str
    source: str = "generated"
    enabled: bool = True


class ToolGenerator:
    """Thin facade.  Runs the full pipeline: Analytics → Evaluate → Promote.

    Usage:
        gen = ToolGenerator(db, llm, registry=registry)
        report_str = await gen.run()   # human-readable summary
    """

    def __init__(self, db: KagekoDB, llm: Any, *, registry: ToolRegistry | None = None):
        self.db = db
        self.llm = llm
        self.registry = registry

    async def run(self) -> str:
        """Run the full QAOA promotion pipeline. Returns a summary string."""
        from kageko.qaoa.analytics import AnalyticsEngine
        from kageko.qaoa.evaluator import Evaluator
        from kageko.qaoa.promoter import Promoter

        # Stage 1: Analytics (no LLM)
        analytics = AnalyticsEngine(self.db)
        report = await analytics.collect()

        lines = [
            f"QAOA Analytics: {report.total_trajectories} trajectories, "
            f"avg {report.avg_turns_per_task:.1f} turns/task",
        ]
        if report.underused_tools:
            lines.append(f"  Underused: {', '.join(report.underused_tools)}")
        if report.unreliable_tools:
            lines.append(f"  Unreliable: {', '.join(report.unreliable_tools)}")
        if report.converging_skills:
            lines.append(f"  Converging skills: {', '.join(report.converging_skills)}")

        # Stage 2: Evaluate (LLM decides)
        evaluator = Evaluator(self.db, self.llm)
        skill_decisions = await evaluator.evaluate_skills(report)
        cluster_decisions = await evaluator.evaluate_clusters(report)

        # Stage 3: Promote
        promoter = Promoter(self.db, self.registry)
        result = await promoter.execute(skill_decisions, cluster_decisions)

        if result.promoted_count:
            lines.append(f"Promoted {result.promoted_count} skill(s) → tool")
        if result.mcp_created:
            lines.append(f"Created {result.mcp_created} MCP server(s)")
        if result.skipped_count:
            lines.append(f"Skipped {result.skipped_count} candidate(s)")

        return "\n".join(lines)
