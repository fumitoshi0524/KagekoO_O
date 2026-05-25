# tests/unit/test_types.py
import pytest
from kageko.types import Message, ToolCall, ToolResult, AgentResult, AgentMode


def test_message_user():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_message_to_dict():
    msg = Message(role="user", content="hello")
    d = msg.to_dict()
    assert d == {"role": "user", "content": "hello"}


def test_tool_call():
    tc = ToolCall(id="call_1", name="file_read", args={"path": "test.py"})
    assert tc.id == "call_1"
    assert tc.name == "file_read"
    assert tc.args == {"path": "test.py"}


def test_tool_result():
    tr = ToolResult(tool_call_id="call_1", content="file contents here")
    assert tr.tool_call_id == "call_1"
    assert tr.content == "file contents here"


def test_tool_result_to_message():
    tr = ToolResult(tool_call_id="call_1", content="file contents")
    msg = tr.to_message()
    assert msg.role == "tool"
    assert msg.content == "file contents"


def test_agent_result():
    result = AgentResult(answer="done", turn_count=3, tokens_used=1500)
    assert result.answer == "done"
    assert result.turn_count == 3
    assert result.trajectory is None


def test_agent_mode_values():
    assert AgentMode.TOOL_USE.value == "tool-use"
    assert AgentMode.QAOA.value == "qaoa"
