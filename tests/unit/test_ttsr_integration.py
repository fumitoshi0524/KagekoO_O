# tests/unit/test_ttsr_integration.py
import re

import pytest

from kageko.agent.ttsr import Correction, StreamInterceptor, StreamRule


@pytest.mark.asyncio
async def test_interceptor_passes_clean_stream():
    """Interceptor must yield tokens unchanged when no rules match."""
    rule = StreamRule(name="no_secret", pattern=re.compile(r"password"), message="Stop leaking secrets")
    interceptor = StreamInterceptor(rules=[rule])

    async def fake_stream():
        for t in ["Hello", " ", "world", "!"]:
            yield t

    result = []
    async for item in interceptor.intercept(fake_stream()):
        result.append(item)

    assert len(result) == 4
    assert all(isinstance(r, str) for r in result)
    assert "".join(result) == "Hello world!"


@pytest.mark.asyncio
async def test_interceptor_stops_on_violation():
    """Interceptor must yield Correction and stop when a rule matches."""
    rule = StreamRule(name="no_secret", pattern=re.compile(r"password"), message="Stop leaking secrets")
    interceptor = StreamInterceptor(rules=[rule])

    async def fake_stream():
        for t in ["The ", "password ", "is ", "1234"]:
            yield t

    result = []
    async for item in interceptor.intercept(fake_stream()):
        result.append(item)

    assert len(result) == 2
    assert result[0] == "The "
    assert isinstance(result[1], Correction)
    assert "secrets" in result[1].message


@pytest.mark.asyncio
async def test_interceptor_multiple_rules():
    """Interceptor must check all rules on each token."""
    rules = [
        StreamRule(name="r1", pattern=re.compile(r"hack"), message="blocked hack"),
        StreamRule(name="r2", pattern=re.compile(r"exploit"), message="blocked exploit"),
    ]
    interceptor = StreamInterceptor(rules=rules)

    async def fake_stream():
        for t in ["I will ", "exploit ", "this"]:
            yield t

    result = []
    async for item in interceptor.intercept(fake_stream()):
        result.append(item)

    assert any(isinstance(r, Correction) for r in result)
