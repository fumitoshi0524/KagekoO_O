# src/kageko/learning/curator.py
from __future__ import annotations

from kageko.data.db import KagekoDB


class Curator:
    """Background maintenance for skills and tools."""

    def __init__(self, db: KagekoDB, stale_days: int = 30):
        self.db = db
        self.stale_days = stale_days

    async def log_action(
        self, action: str, target_type: str, target_name: str, details: str = ""
    ) -> None:
        assert self.db._conn is not None
        from kageko.data.db import _now

        detail = f"[{target_type}:{target_name}] {details}".strip()
        await self.db._conn.execute(
            "INSERT INTO curator_log (action, detail, created_at) VALUES (?, ?, ?)",
            (action, detail, _now()),
        )
        await self.db._conn.commit()

    async def maintain_skills(self) -> list[str]:
        """Review skills and archive stale ones. Returns list of actions taken."""
        actions = []
        return actions

    async def audit_tool_safety(self, tool_name: str, implementation: str) -> bool:
        """Basic safety check for generated tool code."""
        dangerous_patterns = [
            "import os",
            "import subprocess",
            "__import__",
            "eval(",
            "exec(",
            "open(",
            "shutil",
        ]
        for pattern in dangerous_patterns:
            if pattern in implementation:
                await self.log_action(
                    "safety_flag", "tool", tool_name,
                    f"Contains potentially dangerous pattern: {pattern}",
                )
                return False
        return True
