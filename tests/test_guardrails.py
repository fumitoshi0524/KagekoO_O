from __future__ import annotations

import pytest

from kageko.agent.guardrails import GuardrailConfig, ToolCallSignature, ToolGuardrail


def test_signature_deterministic():
    sig1 = ToolCallSignature("read_file", {"path": "a.py", "line": 10})
    sig2 = ToolCallSignature("read_file", {"line": 10, "path": "a.py"})
    assert sig1.hash == sig2.hash


def test_signature_different_tools():
    sig1 = ToolCallSignature("read_file", {"path": "a.py"})
    sig2 = ToolCallSignature("write_file", {"path": "a.py"})
    assert sig1.hash != sig2.hash


def test_warn_on_repeated_calls():
    guardrail = ToolGuardrail()
    sig = ToolCallSignature("read_file", {"path": "a.py"})
    guardrail.check(sig)
    decision = guardrail.check(sig)
    assert decision.action == "warn"


def test_block_on_repeated_calls():
    guardrail = ToolGuardrail()
    sig = ToolCallSignature("run_bash", {"command": "ls"})
    for _ in range(4):
        guardrail.check(sig)
    decision = guardrail.check(sig)
    assert decision.action == "block"


def test_halt_on_repeated_failures():
    guardrail = ToolGuardrail()
    sig = ToolCallSignature("run_bash", {"command": "npm test"})
    for _ in range(7):
        guardrail.check(sig, failed=True)
    decision = guardrail.check(sig, failed=True)
    assert decision.action == "halt"


def test_idempotent_no_progress():
    guardrail = ToolGuardrail()
    sig = ToolCallSignature("read_file", {"path": "missing.txt"})
    guardrail.check(sig, failed=True)
    decision = guardrail.check(sig, failed=True)
    assert decision.action == "warn"
    for _ in range(3):
        guardrail.check(sig, failed=True)
    decision = guardrail.check(sig, failed=True)
    assert decision.action in ("block", "halt")


def test_different_calls_no_interference():
    guardrail = ToolGuardrail()
    sig1 = ToolCallSignature("read_file", {"path": "a.py"})
    sig2 = ToolCallSignature("read_file", {"path": "b.py"})
    for _ in range(4):
        guardrail.check(sig1)
    d1 = guardrail.check(sig1)
    d2 = guardrail.check(sig2)
    assert d1.action == "block"
    assert d2.action == "allow"


def test_reset():
    guardrail = ToolGuardrail()
    sig = ToolCallSignature("run_bash", {"command": "ls"})
    for _ in range(4):
        guardrail.check(sig)
    guardrail.reset()
    decision = guardrail.check(sig)
    assert decision.action == "allow"
