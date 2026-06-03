from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kageko.data.db import KagekoDB

logger = logging.getLogger("kageko.learning.curator")


class SkillState(Enum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"


@dataclass
class CuratorConfig:
    stale_days: int = 30
    archive_days: int = 90
    interval_hours: int = 168
    state_path: Path = field(
        default_factory=lambda: Path.home() / ".kageko" / "skills" / ".curator_state"
    )


class Curator:
    """Background maintenance — Hermes-aligned 5-stage pipeline.

    Runs on a configurable cycle (default: 7 days).  Stages:
      1. State transitions  — active → stale → archive (based on last_used)
      2. Overlap detection  — flag skills with identical triggers
      3. Safety audit       — scan generated tools for dangerous patterns
      4. QAOA Analytics     — collect trajectory stats (no LLM)
      5. QAOA Review        — LLM evaluates → promotes (skill→tool, cluster→MCP)
    """

    def __init__(self, db: KagekoDB, config: CuratorConfig | None = None, *, llm=None, registry=None):
        self.db = db
        self.config = config or CuratorConfig()
        self._llm = llm        # for QAOA stage
        self._registry = registry  # for QAOA stage

    # ── Wire LLM/registry after construction (avoids circular imports) ──

    def wire_llm(self, llm):
        self._llm = llm

    def wire_registry(self, registry):
        self._registry = registry

    async def log_action(
        self, action: str, target_type: str, target_name: str, details: str = ""
    ) -> None:
        detail = f"[{target_type}:{target_name}] {details}".strip()
        await self.db.log_curator_action(action, detail)

    async def maybe_run(self) -> bool:
        """Inactivity-triggered: run only if interval_hours have passed."""
        state = self._load_state()
        if time.time() - state.get("last_run", 0) < self.config.interval_hours * 3600:
            return False
        await self.maintain()
        return True

    async def maintain(self) -> list[str]:
        """Run full maintenance cycle — all 4 stages. Returns list of actions taken."""
        actions = []
        # Stage 1: state transitions
        actions += await self._transition_states()
        # Stage 2: overlap detection
        actions += await self._grade_and_consolidate()
        # Stage 3: safety audit existing tools
        actions += await self._audit_tools()
        # Stage 4: QAOA — analytics → LLM evaluation → promotion
        qaoa_actions = await self._qaoa_review()
        if qaoa_actions:
            actions += qaoa_actions
        self._save_state()
        logger.info("Curator maintenance: %d actions", len(actions))
        return actions

    async def run_qaoa_pipeline(self) -> str:
        """Public entry point for manual QAOA trigger (/qaoa-generate, agent tool).

        Runs the full pipeline: Analytics → Evaluate → Promote.
        Returns a human-readable summary string.
        """
        if not self._llm:
            return "QAOA pipeline: no LLM wired."

        from kageko.qaoa.tool_generator import ToolGenerator

        gen = ToolGenerator(self.db, self._llm, registry=self._registry)
        summary = await gen.run()
        return f"QAOA pipeline complete.\n{summary}"

    async def _qaoa_review(self) -> list[str]:
        """QAOA pipeline — Analytics → Evaluate → Promote.

        Run during Curator maintenance. LLM makes all decisions;
        no hardcoded thresholds.
        """
        if not self._llm:
            return []
        try:
            from kageko.qaoa.tool_generator import ToolGenerator

            gen = ToolGenerator(self.db, self._llm, registry=self._registry)
            summary = await gen.run()
            await self.log_action("qaoa", "review", "", summary)
            return [summary]
        except Exception:
            logger.debug("QAOA review failed", exc_info=True)
            return []

    async def _grade_and_consolidate(self) -> list[str]:
        """Hermes-style grading: flag skills with identical triggers for consolidation."""
        actions = []
        skills = await self.db.get_skills_all()
        if len(skills) < 2:
            return actions
        # Group by trigger
        by_trigger: dict[str, list] = {}
        for s in skills:
            trigger = getattr(s, "trigger", "") or ""
            if trigger:
                by_trigger.setdefault(trigger, []).append(s.name)
        for trigger, names in by_trigger.items():
            if len(names) >= 2:
                msg = f"overlap: {', '.join(names)} share trigger '{trigger}'"
                actions.append(msg)
                await self.log_action("overlap_detected", "skill", ", ".join(names), f"shared trigger: {trigger}")
        return actions

    async def _transition_states(self) -> list[str]:
        """Transition skills: active -> stale -> archived based on last_used."""
        actions = []
        now = time.time()
        stale_cutoff = now - self.config.stale_days * 86400
        archive_cutoff = now - self.config.archive_days * 86400

        # active -> stale
        cursor = await self.db._conn.execute(
            "SELECT name FROM skills WHERE pinned = 0 AND last_used < ? AND state = 'active'",
            (stale_cutoff,),
        )
        rows = await cursor.fetchall()
        for row in rows:
            await self.db.write_with_retry(
                "UPDATE skills SET state = 'stale' WHERE name = ?", (row[0],),
            )
            msg = f"stale: {row[0]}"
            actions.append(msg)
            await self.log_action("state_change", "skill", row[0], "active -> stale")

        # stale -> archived
        cursor = await self.db._conn.execute(
            "SELECT name FROM skills WHERE pinned = 0 AND last_used < ? AND state = 'stale'",
            (archive_cutoff,),
        )
        rows = await cursor.fetchall()
        for row in rows:
            await self.db.write_with_retry(
                "UPDATE skills SET state = 'archived' WHERE name = ?", (row[0],),
            )
            msg = f"archived: {row[0]}"
            actions.append(msg)
            await self.log_action("state_change", "skill", row[0], "stale -> archived")

        return actions

    async def _audit_tools(self) -> list[str]:
        """Audit generated tools for safety."""
        actions = []
        cursor = await self.db._conn.execute(
            "SELECT name, implementation FROM tools WHERE source = 'generated'"
        )
        rows = await cursor.fetchall()
        for row in rows:
            if not await self.audit_tool_safety(row[0], row[1] or ""):
                await self.db.write_with_retry(
                    "UPDATE tools SET enabled = 0 WHERE name = ?", (row[0],),
                )
                msg = f"disabled: {row[0]}"
                actions.append(msg)
                await self.log_action("safety_disable", "tool", row[0], "dangerous patterns found")
        return actions

    async def audit_tool_safety(self, tool_name: str, implementation: str) -> bool:
        """Basic safety check for generated tool code."""
        dangerous_patterns = [
            "import os", "import subprocess", "__import__",
            "eval(", "exec(", "open(", "shutil",
        ]
        for pattern in dangerous_patterns:
            if pattern in implementation:
                await self.log_action(
                    "safety_flag", "tool", tool_name,
                    f"Contains potentially dangerous pattern: {pattern}",
                )
                return False
        return True

    def _load_state(self) -> dict:
        try:
            if self.config.state_path.exists():
                return json.loads(self.config.state_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
        return {"last_run": 0}

    def _save_state(self) -> None:
        state = {"last_run": time.time()}
        self.config.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.config.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        tmp.replace(self.config.state_path)
