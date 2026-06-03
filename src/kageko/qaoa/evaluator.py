"""QAOA Evaluator — LLM-driven promotion decision engine.

Builds structured reports from Analytics data, asks the LLM to decide:
  1. Which skills are ready to become tools?  → generate handler code
  2. Which tool clusters deserve an MCP server?  → generate FastMCP server

No hardcoded thresholds.  The LLM is the judge.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kageko.types import Message

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB
    from kageko.qaoa.analytics import AnalyticsReport

logger = logging.getLogger("kageko.qaoa.evaluator")


@dataclass
class PromotionDecision:
    target: str                           # skill name or cluster domain
    action: str                           # "promote_to_tool" | "promote_to_mcp" | "skip"
    reason: str                           # LLM's explanation
    handler_code: str = ""                # for tool promotion
    handler_schema: dict | None = None    # JSON Schema for the new tool
    handler_description: str = ""         # English one-liner
    mcp_name: str = ""                    # for MCP promotion
    mcp_server_code: str = ""             # FastMCP server body


@dataclass
class EvaluationReport:
    decisions: list[PromotionDecision] = field(default_factory=list)
    promoted_count: int = 0
    skipped_count: int = 0
    mcp_created: int = 0


_SKILL_EVAL_PROMPT = """\
You are a tool architect.  Review these skill candidates and decide which
ones are ready to be promoted from a text-based skill into a registered tool.

A skill is ready when:
- Its execution steps have stabilized (same tool sequence every time).
- It has a clear, stable input signature (what parameters does it need?).
- Promoting to a tool would make the agent faster (no more reading docs).

For each skill you decide to promote:
1. Write a concise "description" field (one sentence, English).
2. Define the "parameters" as a JSON Schema (type: object, properties: {...}, required: [...]).
3. Write the "implementation" — a Python function body with a `def execute(...)` entry point.
   Base the implementation on the skill's steps AND the trajectory examples.
   Use only standard library + the imports mentioned in the skill/trajectories.
   The execute function receives the parameters from the schema as kwargs.

For skills NOT ready, explain why in one sentence.

Return ONLY a JSON array of decision objects:
[
  {{
    "skill_name": "...",
    "action": "promote_to_tool" | "skip",
    "reason": "one sentence explaining why",
    "description": "...",         // only if promote
    "parameters": {{ ... }},      // only if promote — JSON Schema
    "implementation": "def execute(...):\\n    ..."  // only if promote
  }}
]

Skills to evaluate:
{skill_reports}

Decisions (JSON array):"""


_CLUSTER_EVAL_PROMPT = """\
You are an MCP server architect.  Review these tool clusters and decide
which ones should be bundled into an MCP server.

A cluster deserves an MCP server when:
- The tools share a common domain, library, or data format.
- Together they form a coherent "service" that could be useful outside this agent.
- The combined tools are non-trivial (not just one-liners).

Not every cluster needs an MCP.  A single tool might be complex enough
(>80 lines) to warrant its own MCP.  Three loose tools with no shared
logic might be better left as separate tools.

For clusters you decide to promote:
1. Give a name for the MCP server (kebab-case).
2. Write the full FastMCP server code (Python, using `from mcp.server.fastmcp import FastMCP`).
   - The server should expose one tool per cluster member.
   - Reuse the existing implementation logic from each tool.
   - Include proper type hints and docstrings.

For clusters NOT ready, explain why.

Return ONLY a JSON array of decision objects:
[
  {{
    "cluster_domain": "...",
    "action": "promote_to_mcp" | "skip",
    "reason": "one sentence explaining why",
    "mcp_name": "...",             // only if promote
    "mcp_server_code": "..."       // only if promote — full FastMCP server
  }}
]

Tool clusters to evaluate:
{cluster_reports}

Decisions (JSON array):"""


class Evaluator:
    """LLM-driven promotion evaluation.

    Collects analytics data, builds structured reports, asks the LLM
    to make promotion decisions (no hardcoded thresholds).
    """

    def __init__(self, db: KagekoDB, llm):
        self.db = db
        self.llm = llm

    async def evaluate_skills(self, report: AnalyticsReport) -> list[PromotionDecision]:
        """Evaluate all active skills for tool-readiness."""
        active_skills = await self.db.get_skills_all()
        active_skills = [s for s in active_skills if getattr(s, "state", "active") == "active"]
        if not active_skills:
            return []

        # Build per-skill report block
        blocks: list[str] = []
        for s in active_skills:
            name = s.name
            act = report.skill_activity.get(name)
            if act is None:
                blocks.append(f"## {name}\n  Views: 0\n  Uses: 0\n  Steps: unknown\n")
                continue

            converging = "yes" if act.steps_converging else "no"
            blocks.append(
                f"## {name}\n"
                f"  Description: {getattr(s, 'description', '')[:120]}\n"
                f"  Skill views (skill_view calls): {act.views}\n"
                f"  Uses in trajectories: {act.uses_in_trajectories}\n"
                f"  Average steps: {act.avg_steps:.1f}\n"
                f"  Recent step counts: {act.recent_steps}\n"
                f"  Steps converging: {converging}\n"
                f"  Current steps (from skill content):\n"
                f"    {getattr(s, 'content', '')[:500]}\n"
            )

        prompt = _SKILL_EVAL_PROMPT.format(skill_reports="\n".join(blocks))

        try:
            response = await self.llm.chat([Message(role="user", content=prompt)])
            raw = response.content or ""
            decisions = self._parse_decisions(raw, "skill_name")
        except Exception:
            logger.warning("Skill eval LLM call failed", exc_info=True)
            return []

        results: list[PromotionDecision] = []
        for d in decisions:
            action = d.get("action", "skip")
            results.append(PromotionDecision(
                target=d.get("skill_name", "?"),
                action=action,
                reason=d.get("reason", ""),
                handler_code=d.get("implementation", ""),
                handler_schema=d.get("parameters"),
                handler_description=d.get("description", ""),
            ))

        logger.info("Evaluator skills: %d promote, %d skip",
                     sum(1 for r in results if r.action == "promote_to_tool"),
                     sum(1 for r in results if r.action == "skip"))
        return results

    async def evaluate_clusters(self, report: AnalyticsReport) -> list[PromotionDecision]:
        """Evaluate tool clusters for MCP readiness."""
        if not report.clusters:
            return []

        blocks: list[str] = []
        for c in report.clusters:
            blocks.append(
                f"## cluster: {c.domain}\n"
                f"  Tools: {', '.join(c.tool_names)}\n"
                f"  Shared imports: {', '.join(c.shared_imports) if c.shared_imports else 'none'}\n"
                f"  Total implementation lines: {c.total_lines}\n"
            )

        prompt = _CLUSTER_EVAL_PROMPT.format(cluster_reports="\n".join(blocks))

        try:
            response = await self.llm.chat([Message(role="user", content=prompt)])
            raw = response.content or ""
            decisions = self._parse_decisions(raw, "cluster_domain")
        except Exception:
            logger.warning("Cluster eval LLM call failed", exc_info=True)
            return []

        results: list[PromotionDecision] = []
        for d in decisions:
            action = d.get("action", "skip")
            results.append(PromotionDecision(
                target=d.get("cluster_domain", "?"),
                action=action,
                reason=d.get("reason", ""),
                mcp_name=d.get("mcp_name", ""),
                mcp_server_code=d.get("mcp_server_code", ""),
            ))

        logger.info("Evaluator clusters: %d promote, %d skip",
                     sum(1 for r in results if r.action == "promote_to_mcp"),
                     sum(1 for r in results if r.action == "skip"))
        return results

    # ── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_decisions(raw: str, name_key: str) -> list[dict]:
        """Parse LLM response into a list of decision dicts.

        Handles markdown fences and plain JSON.
        """
        import re
        text = raw.strip()
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and name_key in data:
                return [data]
        except json.JSONDecodeError:
            pass
        # Try to find embedded array
        m = re.search(r'\[.*\]', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return []
