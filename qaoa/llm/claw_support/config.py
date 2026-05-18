"""Map Kageko Settings to kwargs for constructing :class:`~qaoa.llm.claw.KagekoAgent`."""

from __future__ import annotations

from typing import Any

from ...config.constants import AgentName
from ...config.settings import Settings


def claw_agent_kwargs_from_settings(settings: Settings) -> dict[str, Any]:
    """Return a dict of common constructor kwargs (working directory, max_iterations hints).

    Typical external agent APIs expose many parameters; KagekoAgent uses the same ``Agent``
    base and reads ``coder`` agent config for model-related settings elsewhere
    (provider construction in the TUI). This helper centralizes non-provider fields.
    """
    agent_cfg = settings.get_agent_config(AgentName.CODER)
    max_iter = getattr(agent_cfg, "max_iterations", None) or 100
    wd = str(getattr(settings, "working_directory", None) or "").strip() or "."
    return {
        "working_directory": wd,
        "max_iterations": int(max_iter),
    }
