# tests/unit/test_ttsr.py
import pytest
import re
from kageko.agent.ttsr import StreamRule, StreamInterceptor, Correction


def test_stream_rule_matches():
    rule = StreamRule(
        name="no-import-os",
        pattern=re.compile(r"import\s+os"),
        message="Do not import os directly. Use pathlib instead.",
    )
    assert rule.matches("import os")


def test_stream_rule_no_match():
    rule = StreamRule(
        name="no-import-os",
        pattern=re.compile(r"import\s+os"),
        message="Use pathlib.",
    )
    assert not rule.matches("from pathlib import Path")


@pytest.mark.asyncio
async def test_interceptor_yields_normal_tokens():
    rule = StreamRule(
        name="test",
        pattern=re.compile(r"BAD"),
        message="Don't do that",
    )
    interceptor = StreamInterceptor(rules=[rule])

    tokens = [{"text": "hello "}, {"text": "world"}]
    result = []
    async for t in interceptor._simulate(tokens):
        result.append(t)

    assert len(result) == 2
    assert result[0]["text"] == "hello "


@pytest.mark.asyncio
async def test_interceptor_detects_violation():
    rule = StreamRule(
        name="no-bad",
        pattern=re.compile(r"BAD"),
        message="Stop!",
    )
    interceptor = StreamInterceptor(rules=[rule])

    tokens = [{"text": "this is "}, {"text": "BAD stuff"}]
    result = []
    async for t in interceptor._simulate(tokens):
        result.append(t)

    assert len(result) == 2
    assert isinstance(result[1], Correction)
    assert result[1].message == "Stop!"
