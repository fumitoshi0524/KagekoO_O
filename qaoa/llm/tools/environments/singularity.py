# QAOA category: system, domain: technology
"""Singularity/Apptainer backend (placeholder — full execution stack not ported)."""

from __future__ import annotations

from .base import BaseEnvironment

_CLAW_SUPPORT_MAP = "qaoa/llm/claw_support/KAAGEKO_SUPPORT_MAP.md"


class SingularityEnvironment(BaseEnvironment):
    def execute(
        self,
        command: str,
        cwd: str = "",
        *,
        timeout: int | None = None,
        stdin_data: str | None = None,
    ) -> dict[str, str | int]:
        _ = (command, cwd, timeout, stdin_data)
        raise RuntimeError(
            "SingularityEnvironment is not implemented in kageko. "
            "Host `singularity` / `apptainer` CLI integration is not wired here. "
            f"See `{_CLAW_SUPPORT_MAP}`. "
            "See external reference implementations for full Singularity wiring."
        )

    def cleanup(self) -> None:
        return None
