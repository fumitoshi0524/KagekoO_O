"""System prompt additions for /claw (Kageko-localized) mode."""

from __future__ import annotations


def get_claw_mode_system_suffix() -> str:
    """Short suffix appended to the coder system prompt in Kageko mode.

    Keeps behavior explicit for the model: same tool surface as the default
    coder agent, routed through the dedicated Claw-mode execution branch.
    """
    return (
        "\n\n## Claw mode\n"
        "You are running in **Claw mode**: multi-turn tool use follows the same "
        "rules as the default coding agent, with full read/write tools unless "
        "the session is in a read-only planning state elsewhere."
    )
