from __future__ import annotations

from qaoa.integration.hooks import (
    HooksEngine, HookHandler, HookEvent, HookContext, HookResult,
)


def test_hooks_engine_register_and_dispatch():
    engine = HooksEngine()
    handler = HookHandler(
        event=HookEvent.PRE_TOOL_USE,
        handler_type="command",
        command="echo allow",
    )
    engine.register(handler)
    assert engine.has_handlers(HookEvent.PRE_TOOL_USE)

    ctx = HookContext(event=HookEvent.PRE_TOOL_USE, tool_name="file.write", tool_input="test")
    result = engine.dispatch(ctx)
    assert result == HookResult.ALLOW  # "echo allow" outputs "allow"


def test_hooks_engine_deny():
    engine = HooksEngine()
    handler = HookHandler(
        event=HookEvent.PRE_TOOL_USE,
        handler_type="command",
        command="echo deny",
    )
    engine.register(handler)

    ctx = HookContext(event=HookEvent.PRE_TOOL_USE, tool_name="rm")
    result = engine.dispatch(ctx)
    assert result == HookResult.DENY


def test_hooks_engine_no_handlers():
    engine = HooksEngine()
    ctx = HookContext(event=HookEvent.SKILL_GENERATED, skill_name="test")
    result = engine.dispatch(ctx)
    assert result == HookResult.CONTINUE


def test_hooks_engine_from_config():
    config = [
        {"event": "PostToolUse", "type": "command", "command": "echo logged"},
        {"event": "SkillGenerated", "type": "prompt", "prompt": "Review this"},
    ]
    engine = HooksEngine.from_config(config)
    assert engine.has_handlers(HookEvent.POST_TOOL_USE)
    assert engine.has_handlers(HookEvent.SKILL_GENERATED)
    assert not engine.has_handlers(HookEvent.PRE_TOOL_USE)


def test_hooks_engine_unregister():
    engine = HooksEngine()
    handler = HookHandler(event=HookEvent.SKILL_ACTIVATED, handler_type="command", command="echo")
    engine.register(handler)
    assert engine.has_handlers(HookEvent.SKILL_ACTIVATED)
    engine.unregister(HookEvent.SKILL_ACTIVATED, handler)
    assert not engine.has_handlers(HookEvent.SKILL_ACTIVATED)


def test_hooks_engine_clear():
    engine = HooksEngine()
    engine.register(HookHandler(event=HookEvent.PRE_TOOL_USE, handler_type="command", command="echo"))
    engine.clear()
    assert not engine.has_handlers(HookEvent.PRE_TOOL_USE)


def test_all_hook_events():
    events = list(HookEvent)
    assert HookEvent.PRE_TOOL_USE in events
    assert HookEvent.POST_TOOL_USE in events
    assert HookEvent.SKILL_GENERATED in events
    assert HookEvent.SKILL_EVALUATED in events
    assert HookEvent.SKILL_ACTIVATED in events


def test_hook_context_creation():
    ctx = HookContext(
        event=HookEvent.POST_TOOL_USE,
        tool_name="bash.run",
        tool_input="ls",
        tool_output="file1",
        skill_name="scaffolder",
        session_id="abc123",
        metadata={"extra": "data"},
    )
    assert ctx.tool_name == "bash.run"
    assert ctx.tool_output == "file1"
    assert ctx.metadata["extra"] == "data"
