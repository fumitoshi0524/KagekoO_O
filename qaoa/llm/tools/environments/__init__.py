# QAOA category: system, domain: technology
"""Kageko-aligned execution environments (local, docker, ...) for future bash/tool integration.

See :mod:`qaoa.llm.tools.bash` for the default async shell used by the agent.
"""

from __future__ import annotations

from .base import BaseEnvironment, get_sandbox_dir
from .docker import DockerEnvironment
from .factory import create_environment
from .interrupt import is_interrupted, set_interrupt_check
from .local import LocalEnvironment, find_bash
from .persistent_shell import PersistentShellMixin
from .ssh import SSHEnvironment

__all__ = [
    "BaseEnvironment",
    "DockerEnvironment",
    "LocalEnvironment",
    "PersistentShellMixin",
    "SSHEnvironment",
    "create_environment",
    "find_bash",
    "get_sandbox_dir",
    "is_interrupted",
    "set_interrupt_check",
]
