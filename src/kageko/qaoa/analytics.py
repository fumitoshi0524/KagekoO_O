"""QAOA Analytics — pure stats, no LLM calls.

Feeds the Curator with data it uses to make promotion decisions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB

logger = logging.getLogger("kageko.qaoa.analytics")


@dataclass
class ToolStats:
    """Per-tool statistics from trajectory data."""
    name: str
    calls: int = 0
    errors: int = 0
    avoided: bool = False  # registered but never called in recent sessions

    @property
    def error_rate(self) -> float:
        return self.errors / self.calls if self.calls > 0 else 0.0

    @property
    def reliability(self) -> str:
        if self.calls == 0:
            return "unknown"
        if self.error_rate <= 0.05:
            return "high"
        if self.error_rate <= 0.2:
            return "medium"
        return "low"


@dataclass
class SkillActivity:
    """Per-skill activity from DB + trajectory cross-reference."""
    name: str
    views: int = 0          # skill_view calls (from last_used bumps)
    uses_in_trajectories: int = 0   # mentions in QAOA trajectories
    avg_steps: float = 0.0  # average steps per use
    recent_steps: list[int] = field(default_factory=list)  # last 5 use step counts

    @property
    def steps_converging(self) -> bool:
        """Are recent executions taking fewer steps? → workflow is stabilizing."""
        if len(self.recent_steps) < 3:
            return False
        return self.recent_steps[-1] <= self.recent_steps[0]


@dataclass
class DomainCluster:
    """A group of tools sharing the same domain/category."""
    domain: str
    tool_names: list[str] = field(default_factory=list)
    shared_imports: list[str] = field(default_factory=list)
    total_lines: int = 0


@dataclass
class AnalyticsReport:
    """Aggregated stats for Curator consumption."""
    tool_stats: dict[str, ToolStats] = field(default_factory=dict)
    skill_activity: dict[str, SkillActivity] = field(default_factory=dict)
    clusters: list[DomainCluster] = field(default_factory=list)
    total_trajectories: int = 0
    avg_turns_per_task: float = 0.0

    @property
    def underused_tools(self) -> list[str]:
        """Tools registered but never called in recent sessions."""
        return [n for n, s in self.tool_stats.items() if s.avoided]

    @property
    def unreliable_tools(self) -> list[str]:
        """Tools with error rate > 20%."""
        return [n for n, s in self.tool_stats.items() if s.reliability == "low"]

    @property
    def converging_skills(self) -> list[str]:
        """Skills whose execution is stabilizing → prime candidates for promotion."""
        return [n for n, a in self.skill_activity.items() if a.steps_converging]


class AnalyticsEngine:
    """Pure-data analytics over QAOA trajectories, skills, and tools.

    Feeds the evaluator by providing structured stats without any LLM calls.
    """

    def __init__(self, db: KagekoDB):
        self.db = db

    async def collect(self, lookback_days: int = 30) -> AnalyticsReport:
        """Gather all stats from the past N days. Returns a report."""
        report = AnalyticsReport()

        # Tool stats from trajectories
        trajectories = await self.db.get_recent_trajectories(days=lookback_days)
        report.total_trajectories = len(trajectories)

        tool_calls: dict[str, list[bool]] = {}  # name → [True=ok, False=error]
        for traj in trajectories:
            for action in traj.get("actions", []):
                name = action.get("tool", "?")
                is_err = action.get("is_error", False) or "ERROR" in str(action.get("observation", ""))
                tool_calls.setdefault(name, []).append(not is_err)

        for name, results in tool_calls.items():
            report.tool_stats[name] = ToolStats(
                name=name,
                calls=len(results),
                errors=sum(1 for r in results if not r),
            )

        # Detected avoided tools (registered in DB but zero calls in trajectories)
        all_tools = await self.db.get_tools_generated()
        for t in all_tools:
            tname = t["name"]
            if tname not in tool_calls:
                report.tool_stats[tname] = ToolStats(name=tname, avoided=True)

        # Skill activity
        skills = await self.db.get_skills_all()
        for s in skills:
            name = s.name
            act = SkillActivity(name=name)
            # Count views from last_used
            lu = getattr(s, "last_used", 0)
            act.views = 1 if lu > 0 else 0  # at least viewed once

            # Cross-reference with trajectories: find mentions
            steps_per_use: list[int] = []
            for traj in trajectories:
                actions = traj.get("actions", [])
                # If the trajectory contains tool calls resembling skill steps
                has_skill_mention = False
                step_count = 0
                for a in actions:
                    tool = a.get("tool", "")
                    if tool not in ("echo", "todo_add", "todo_list", "memory_list", "skill_list"):
                        step_count += 1
                    # Crude detection: does the query or answer mention the skill name?
                query = (traj.get("query") or "").lower()
                answer = (traj.get("answer") or "").lower()
                if name.lower() in query or name.lower() in answer:
                    has_skill_mention = True
                    steps_per_use.append(step_count)

            act.uses_in_trajectories = len(steps_per_use)
            act.recent_steps = steps_per_use[-5:] if steps_per_use else []
            if steps_per_use:
                act.avg_steps = sum(steps_per_use) / len(steps_per_use)

            report.skill_activity[name] = act

        # Domain clusters (group tools by category)
        tools_by_cat: dict[str, list[dict]] = {}
        for t in all_tools:
            cat = t.get("category", "utility")
            tools_by_cat.setdefault(cat, []).append(t)

        for cat, tools in tools_by_cat.items():
            if len(tools) >= 1:  # single-tool clusters still reported
                cluster = DomainCluster(domain=cat, tool_names=[t["name"] for t in tools])
                # Detect shared imports
                all_imports: list[tuple[str, str]] = []
                for t in tools:
                    impl = t.get("implementation", "") or ""
                    for line in impl.split("\n"):
                        if line.strip().startswith(("import ", "from ")):
                            all_imports.append((t["name"], line.strip()))
                # Imports shared by ≥2 tools
                from collections import Counter
                import_counter = Counter(i[1] for i in all_imports)
                cluster.shared_imports = [imp for imp, c in import_counter.items() if c >= 2]
                cluster.total_lines = sum(len((t.get("implementation", "") or "").split("\n")) for t in tools)
                report.clusters.append(cluster)

        # Average turns per task
        if trajectories:
            steps_per_traj = [len(t.get("actions", [])) for t in trajectories]
            report.avg_turns_per_task = sum(steps_per_traj) / len(steps_per_traj)

        return report
