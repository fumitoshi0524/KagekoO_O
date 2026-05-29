# tests/unit/test_permissions.py
import pytest
from unittest.mock import AsyncMock
from kageko.agent.permissions import PermissionPipeline, Decision, SecurityMode, RuleEngine
from kageko.types import ToolCall


@pytest.fixture
def pipeline():
    return PermissionPipeline(mode=SecurityMode.INTERACTIVE, prompt_fn=AsyncMock(return_value=Decision.ALLOW))


def test_read_only_mode_denies_writes(pipeline):
    pipeline.mode = SecurityMode.READ_ONLY
    tc = ToolCall(id="1", name="file_write", args={"path": "x.py", "content": "hi"})
    decision = pipeline._check_mode(tc)
    assert decision == Decision.DENY


def test_read_only_mode_allows_reads(pipeline):
    pipeline.mode = SecurityMode.READ_ONLY
    tc = ToolCall(id="1", name="file_read", args={"path": "x.py"})
    decision = pipeline._check_mode(tc)
    assert decision is None


def test_dangerous_pattern_blocks_rm_rf(pipeline):
    tc = ToolCall(id="1", name="bash", args={"command": "rm -rf /"})
    decision = pipeline.rule_engine.check(tc)
    assert decision == Decision.DENY


def test_dangerous_pattern_allows_safe_command(pipeline):
    tc = ToolCall(id="1", name="bash", args={"command": "ls -la"})
    decision = pipeline.rule_engine.check(tc)
    assert decision is None


def test_high_risk_tools_require_sandbox(pipeline):
    tc = ToolCall(id="1", name="bash", args={"command": "echo hi"})
    assert tc.name in pipeline.HIGH_RISK_TOOLS


@pytest.mark.asyncio
async def test_full_pipeline_allow_read(pipeline):
    pipeline.mode = SecurityMode.PERMISSIVE
    tc = ToolCall(id="1", name="file_read", args={"path": "test.py"})
    decision = await pipeline.check(tc)
    assert decision == Decision.ALLOW


@pytest.mark.asyncio
async def test_full_pipeline_deny_dangerous(pipeline):
    tc = ToolCall(id="1", name="bash", args={"command": "rm -rf /"})
    decision = await pipeline.check(tc)
    assert decision == Decision.DENY


@pytest.mark.asyncio
async def test_interactive_mode_requires_prompt_fn():
    pipeline = PermissionPipeline(mode=SecurityMode.INTERACTIVE)
    tc = ToolCall(id="1", name="bash", args={"command": "ls"})
    with pytest.raises(PermissionError):
        await pipeline.check(tc)


@pytest.mark.asyncio
async def test_interactive_prompt_fn_called():
    async def deny_fn(tc): return Decision.DENY
    pipeline = PermissionPipeline(mode=SecurityMode.INTERACTIVE, prompt_fn=deny_fn)
    tc = ToolCall(id="1", name="bash", args={"command": "ls"})
    decision = await pipeline.check(tc)
    assert decision == Decision.DENY
