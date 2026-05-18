# QAOA category: system, domain: technology
"""Sudo command transformation.

Standalone; no external agent imports. Interactive password prompt is omitted; set ``SUDO_PASSWORD``
or rely on passwordless sudo.
"""

from __future__ import annotations

import os
import re

def transform_sudo_command(command: str) -> tuple[str, str | None]:
    """Replace bare ``sudo`` with ``sudo -S -p ''`` when ``SUDO_PASSWORD`` is set.

    Returns ``(transformed_command, sudo_stdin)`` where ``sudo_stdin`` is the
    password plus newline for stdin, or ``None``.
    """
    if not re.search(r"\bsudo\b", command):
        return command, None

    sudo_password = os.getenv("SUDO_PASSWORD", "").strip()
    if not sudo_password:
        return command, None

    def replace_sudo(_match: re.Match[str]) -> str:
        return "sudo -S -p ''"

    transformed = re.sub(r"\bsudo\b", replace_sudo, command)
    return transformed, sudo_password + "\n"
