"""Backward-compat re-export from qaoa.tools.builtins."""

from __future__ import annotations

from ..tools.builtins import register_builtin_tools

class BuiltinToolPack:
    def __init__(self, workspace, skills_dir=None):
        self.workspace = workspace
        self.skills_dir = skills_dir

    def register(self, registry):
        register_builtin_tools(registry, workspace=self.workspace,
                               skills_dir=self.skills_dir)
