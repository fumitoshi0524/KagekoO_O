"""QAOA Promoter — executes LLM-made promotion decisions.

Skill → Tool: register handler, archive skill.
Tool cluster → MCP: save MCP server file, register as MCP server, remove old tools.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB
    from kageko.tools.registry import ToolRegistry
    from kageko.qaoa.evaluator import PromotionDecision, EvaluationReport
    from kageko.qaoa.analytics import AnalyticsReport

logger = logging.getLogger("kageko.qaoa.promoter")


class Promoter:
    """Executes promotion decisions — skill→tool, tool cluster→mcp."""

    MCP_DIR = Path.home() / ".kageko" / "mcp_servers"

    def __init__(self, db: KagekoDB, registry: ToolRegistry | None = None):
        self.db = db
        self.registry = registry

    async def execute(self, skill_decisions: list[PromotionDecision],
                       cluster_decisions: list[PromotionDecision]) -> EvaluationReport:
        """Execute all promotion decisions. Returns a summary report."""
        report = EvaluationReport()

        for d in skill_decisions:
            if d.action == "promote_to_tool":
                success = await self._promote_skill_to_tool(d)
                if success:
                    report.promoted_count += 1
                else:
                    report.skipped_count += 1
            else:
                report.skipped_count += 1
                await self.db.log_curator_action(
                    "qa_skip", "skill", d.target, f"SKIP: {d.reason}",
                )

        for d in cluster_decisions:
            if d.action == "promote_to_mcp":
                success = await self._promote_cluster_to_mcp(d)
                if success:
                    report.mcp_created += 1
                else:
                    report.skipped_count += 1
            else:
                report.skipped_count += 1
                await self.db.log_curator_action(
                    "qa_skip", "cluster", d.target, f"SKIP: {d.reason}",
                )

        logger.info("Promoter: %d tools, %d MCPs created, %d skipped",
                     report.promoted_count, report.mcp_created, report.skipped_count)
        return report

    # ── Skill → Tool ────────────────────────────────────────────────────

    async def _promote_skill_to_tool(self, d: PromotionDecision) -> bool:
        """Register a new tool from a skill, then archive the skill."""
        if not d.handler_code:
            logger.warning("Promote skip '%s': no handler code", d.target)
            return False

        # Safety audit
        if not await self._audit_code(d.target, d.handler_code):
            await self.db.log_curator_action(
                "qa_reject", "tool", d.target, "failed safety audit",
            )
            return False

        # Persist to DB
        params = d.handler_schema or {"type": "object", "properties": {}, "required": []}
        await self.db.write_with_retry(
            "INSERT OR REPLACE INTO tools (name, schema_json, implementation, description, category, source) "
            "VALUES (?, ?, ?, ?, ?, 'generated')",
            (d.target, json.dumps(params), d.handler_code, d.handler_description or "", "utility"),
        )

        # Hot-load into registry
        if self.registry:
            self._hot_load_tool(d.target, d.handler_description or "", params, d.handler_code)

        # Archive the skill (it's a tool now)
        await self.db.skill_set_state(d.target, "archived")

        await self.db.log_curator_action(
            "qa_promote", "skill→tool", d.target, d.reason,
        )
        logger.info("Promoted skill→tool: %s", d.target)
        return True

    # ── Tool cluster → MCP ──────────────────────────────────────────────

    async def _promote_cluster_to_mcp(self, d: PromotionDecision) -> bool:
        """Save MCP server code, register as MCP server, remove old tools."""
        if not d.mcp_server_code:
            logger.warning("MCP promote skip '%s': no server code", d.target)
            return False

        # Safety audit
        if not await self._audit_code(d.mcp_name, d.mcp_server_code):
            await self.db.log_curator_action(
                "qa_reject", "mcp", d.mcp_name or d.target, "failed safety audit",
            )
            return False

        # Save to disk
        self.MCP_DIR.mkdir(parents=True, exist_ok=True)
        server_path = self.MCP_DIR / f"{d.mcp_name or d.target}.py"
        server_path.write_text(d.mcp_server_code, encoding="utf-8")

        # If we have access to MCP config, register it
        # (Kageko reads mcp_servers from kageko.toml; this writes the server file
        #  so the user can add it manually.  The curator log records it.)
        await self.db.log_curator_action(
            "qa_promote", "cluster→mcp", d.mcp_name or d.target,
            f"Server saved to {server_path}. {d.reason}",
        )

        logger.info("Promoted cluster→mcp: %s → %s", d.target, server_path)
        return True

    # ── Helpers ─────────────────────────────────────────────────────────

    async def _audit_code(self, name: str, code: str) -> bool:
        """Safety-scan generated code."""
        dangerous = [
            "import os", "import subprocess", "__import__",
            "eval(", "exec(", "shutil.rmtree", "os.remove",
            "os.system", "subprocess.call", "subprocess.Popen",
            "requests.delete", "urllib",
        ]
        for pat in dangerous:
            if pat in code:
                logger.warning("Promoter audit '%s': dangerous pattern '%s' — REJECT", name, pat)
                return False
        return True

    def _hot_load_tool(self, name: str, description: str, params: dict, code: str) -> None:
        """Register a generated tool into the live ToolRegistry."""
        if not self.registry:
            return

        from kageko.tools.registry import Tool

        def _make_handler(impl_code: str):
            def handler(**kwargs):
                local_ns = {}
                exec(impl_code, {}, local_ns)
                if "execute" in local_ns:
                    return local_ns["execute"](**kwargs)
                return "[generated tool: no execute function]"
            return handler

        tool = Tool(
            name=name,
            description=description,
            parameters=params,
            handler=_make_handler(code),
            category="utility",
        )
        self.registry.register(tool)
        logger.info("Hot-loaded promoted tool: %s", name)
