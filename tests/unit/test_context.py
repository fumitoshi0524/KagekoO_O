import pytest
from kageko.agent.context import ContextCompressor
from kageko.types import Message


def test_compress_short_messages():
    messages = [
        Message(role="user", content="hi"),
        Message(role="assistant", content="hello"),
    ]
    compressor = ContextCompressor(max_tokens=1000)
    result = compressor.compress(messages, current_tokens=50)
    assert result == messages


def test_compress_estimates_tokens():
    compressor = ContextCompressor(max_tokens=100)
    long_msg = Message(role="user", content="x" * 400)
    tokens = compressor.estimate_tokens([long_msg])
    assert tokens >= 90


def test_compress_preserves_head_and_tail():
    messages = [
        Message(role="system", content="system prompt"),
        Message(role="user", content="a" * 1000),
        Message(role="assistant", content="b" * 1000),
        Message(role="user", content="c" * 1000),
        Message(role="assistant", content="final answer"),
    ]
    compressor = ContextCompressor(max_tokens=100, head_count=1, tail_count=1)
    result = compressor.compress(messages, current_tokens=500)
    assert result[0].role == "system"
    assert result[-1].content == "final answer"
    assert len(result) < len(messages) + 1
