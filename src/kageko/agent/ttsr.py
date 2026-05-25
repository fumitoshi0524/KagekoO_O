# src/kageko/agent/ttsr.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class Correction:
    """A correction message injected when a rule matches."""
    message: str


@dataclass
class StreamRule:
    """A rule that watches stream output for patterns."""
    name: str
    pattern: re.Pattern[str]
    message: str

    def matches(self, text: str) -> bool:
        return bool(self.pattern.search(text))


class StreamInterceptor:
    """Time-traveling stream rules: detect violations mid-stream and inject corrections."""

    def __init__(self, rules: list[StreamRule]):
        self.rules = rules

    async def intercept(self, stream: AsyncIterator[str]) -> AsyncIterator[str | Correction]:
        """Wrap a token stream, yielding tokens or corrections."""
        buffer = ""
        async for token in stream:
            buffer += token
            for rule in self.rules:
                if rule.matches(buffer):
                    yield Correction(message=rule.message)
                    return
            yield token

    async def _simulate(self, tokens: list[dict]) -> AsyncIterator[dict | Correction]:
        """Test helper: simulate a token stream from a list."""
        buffer = ""
        for token in tokens:
            text = token.get("text", "")
            buffer += text
            for rule in self.rules:
                if rule.matches(buffer):
                    yield Correction(message=rule.message)
                    return
            yield token
