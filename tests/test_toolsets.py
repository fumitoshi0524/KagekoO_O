from __future__ import annotations

from kageko.tools.toolsets import CORE_TOOLS, TOOLSETS, resolve_toolset


def test_core_tools_defined():
    assert "read_file" in CORE_TOOLS
    assert "write_file" in CORE_TOOLS
    assert "run_bash" in CORE_TOOLS
    assert "hashline_edit" in CORE_TOOLS


def test_toolset_includes_composition():
    coding = TOOLSETS["coding"]
    assert "read_file" in coding.tools
    resolved = resolve_toolset("coding")
    assert "grep" in resolved


def test_resolve_toolset_no_duplicates():
    resolved = resolve_toolset("gateway")
    assert len(resolved) == len(set(resolved))


def test_safe_toolset_no_mutating():
    resolved = resolve_toolset("safe")
    from kageko.agent.guardrails import MUTATING_TOOLS
    for tool in resolved:
        assert tool not in MUTATING_TOOLS
