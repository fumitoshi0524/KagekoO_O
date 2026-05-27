from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from kageko.agent.context import ContextCompressor, ContextBudget
from kageko.learning.memory import MemoryManager
from kageko.types import Message, ToolCall


@pytest.fixture
def budget():
    return ContextBudget(max_tokens=4000, head_count=2, tail_count=2)


@pytest.fixture
def compressor(budget):
    memory = MagicMock(spec=MemoryManager)
    memory.summarize_tool_result = MagicMock(
        side_effect=lambda name, result: f"[{name}] summarized"
    )
    llm = MagicMock()
    return ContextCompressor(memory=memory, llm=llm, budget=budget)


def test_prune_tool_outputs(compressor):
    messages = [
        Message(role="user", content="run the tests"),
        Message(role="assistant", content="", tool_calls=[
            ToolCall(id="tc1", name="run_bash", args={"command": "pytest"})
        ]),
        Message(role="tool", content="FAILED test_login.py\n" + "x\n" * 100, tool_call_id="tc1", tool_name="run_bash"),
        Message(role="assistant", content="There are failures"),
    ]
    pruned = compressor._prune_tool_outputs(messages)
    tool_msg = [m for m in pruned if m.role == "tool"][0]
    assert "[run_bash]" in tool_msg.content
    assert "summarized" in tool_msg.content
    assert len(tool_msg.content) < 200


def test_strip_images(compressor):
    messages = [
        Message(role="user", content="screenshot please"),
        Message(role="assistant", content="Here is the screenshot", images=[{"type": "image_url", "url": "data:image/png;base64,abc123"}]),
        Message(role="user", content="now fix the button"),
        Message(role="assistant", content="I'll fix it"),
    ]
    stripped = compressor._strip_images(messages)
    img_msg = stripped[1]
    assert img_msg.images is None or len(img_msg.images) == 0
    assert "image" in img_msg.content.lower()


def test_compress_preserves_head_and_tail(compressor):
    long_middle = "x" * 4000  # ~1000 tokens each after estimation
    messages = [
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="first question"),
        Message(role="assistant", content="first answer" + long_middle),
        Message(role="user", content="middle question 1" + long_middle),
        Message(role="assistant", content="middle answer 1" + long_middle),
        Message(role="user", content="middle question 2" + long_middle),
        Message(role="assistant", content="middle answer 2" + long_middle),
        Message(role="user", content="last question" + long_middle),
        Message(role="assistant", content="last answer" + long_middle),
    ]
    current_tokens = compressor.estimate_tokens(messages)
    compressed = compressor.compress(messages, current_tokens=current_tokens)
    assert compressed[0].role == "system"
    assert compressed[1].content == "first question"
    assert compressed[-2].content.startswith("last question")
    assert compressed[-1].content.startswith("last answer")
    assert len(compressed) < len(messages)


def test_compress_noop_when_under_budget(compressor):
    messages = [Message(role="user", content="short"), Message(role="assistant", content="reply")]
    result = compressor.compress(messages, current_tokens=100)
    assert len(result) == len(messages)


def test_anti_thrashing(compressor):
    compressor._consecutive_low_savings = 2
    long_content = "x" * 5000
    messages = [
        Message(role="system", content="system" + long_content),
        Message(role="user", content="question" + long_content),
        Message(role="assistant", content="answer" + long_content),
        Message(role="user", content="q2" + long_content),
        Message(role="assistant", content="a2" + long_content),
    ]
    current_tokens = compressor.estimate_tokens(messages)
    result = compressor.compress(messages, current_tokens=current_tokens)
    assert len(result) == len(messages)
