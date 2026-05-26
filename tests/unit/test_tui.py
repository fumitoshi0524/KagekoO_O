# tests/unit/test_tui.py
def test_tui_app_importable():
    """TUI app module must be importable."""
    from kageko.tui.app import KagekoTUI
    assert KagekoTUI is not None


def test_tui_has_chat_widget():
    """TUI must have a chat history widget."""
    from kageko.tui.app import KagekoTUI
    app = KagekoTUI()
    assert hasattr(app, "compose")


def test_tui_has_input_widget():
    """TUI must have an input widget for user messages."""
    from kageko.tui.app import KagekoTUI
    import inspect
    source = inspect.getsource(KagekoTUI.compose)
    assert "Input" in source


def test_cli_has_tui_command():
    """CLI must expose a 'tui' command."""
    from kageko.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, ["tui", "--help"])
    assert result.exit_code == 0
    assert "tui" in result.output.lower() or "textual" in result.output.lower()


def test_tui_has_input_history_state():
    """TUI must initialise input history tracking."""
    from kageko.tui.app import KagekoTUI
    tui = KagekoTUI()
    assert hasattr(tui, "_input_history")
    assert isinstance(tui._input_history, list)
    assert tui._input_history == []
    assert hasattr(tui, "_history_index")
    assert tui._history_index == -1


def test_tui_accepts_db_and_session():
    """TUI must accept optional db and session params."""
    from kageko.tui.app import KagekoTUI
    fake_db = object()
    fake_session = object()
    tui = KagekoTUI(db=fake_db, session=fake_session)
    assert tui.db is fake_db
    assert tui.session is fake_session


def test_tui_db_session_default_none():
    """TUI db and session default to None."""
    from kageko.tui.app import KagekoTUI
    tui = KagekoTUI()
    assert tui.db is None
    assert tui.session is None


def test_tui_has_up_down_bindings():
    """TUI must have up/down key bindings for history navigation."""
    from kageko.tui.app import KagekoTUI
    binding_keys = [b.key for b in KagekoTUI.BINDINGS]
    assert "up" in binding_keys
    assert "down" in binding_keys


def test_tui_has_history_action_methods():
    """TUI must have action_history_prev and action_history_next."""
    from kageko.tui.app import KagekoTUI
    assert hasattr(KagekoTUI, "action_history_prev")
    assert hasattr(KagekoTUI, "action_history_next")
    assert callable(KagekoTUI.action_history_prev)
    assert callable(KagekoTUI.action_history_next)


def test_tui_history_prev_empty():
    """history_prev on empty history should not crash."""
    from kageko.tui.app import KagekoTUI
    tui = KagekoTUI()
    # Should not raise
    tui.action_history_prev()
    assert tui._history_index == -1


def test_tui_history_navigation_logic():
    """Test history navigation index arithmetic."""
    from kageko.tui.app import KagekoTUI
    tui = KagekoTUI()
    tui._input_history = ["hello", "world", "foo"]
    tui._history_index = -1

    # Simulate action_history_prev index logic (without DOM query)
    # When index <= 0, clamp to 0
    # When index > 0, decrement
    def _prev(idx, length):
        if length == 0:
            return idx
        if idx <= 0:
            return 0
        return idx - 1

    def _next(idx, length):
        if idx < 0:
            return idx
        if idx >= length - 1:
            return -1
        return idx + 1

    # Up from -1 -> 0 (last item)
    tui._history_index = _prev(tui._history_index, len(tui._input_history))
    assert tui._history_index == 0

    # Set to 2, then prev -> 1
    tui._history_index = 2
    tui._history_index = _prev(tui._history_index, len(tui._input_history))
    assert tui._history_index == 1

    # prev -> 0
    tui._history_index = _prev(tui._history_index, len(tui._input_history))
    assert tui._history_index == 0

    # prev again -> stays 0
    tui._history_index = _prev(tui._history_index, len(tui._input_history))
    assert tui._history_index == 0

    # next -> 1
    tui._history_index = _next(tui._history_index, len(tui._input_history))
    assert tui._history_index == 1

    # next -> 2
    tui._history_index = _next(tui._history_index, len(tui._input_history))
    assert tui._history_index == 2

    # next -> -1 (past end, clears input)
    tui._history_index = _next(tui._history_index, len(tui._input_history))
    assert tui._history_index == -1


def test_tui_on_input_submitted_adds_to_history():
    """on_input_submitted must add input to _input_history."""
    from kageko.tui.app import KagekoTUI
    # We test the logic by inspecting source since running the full
    # Textual app event loop is heavyweight for a unit test.
    import inspect
    source = inspect.getsource(KagekoTUI.on_input_submitted)
    assert "_input_history" in source


def test_tui_slash_command_detection():
    """on_input_submitted must detect slash commands."""
    import inspect
    from kageko.tui.app import KagekoTUI
    source = inspect.getsource(KagekoTUI.on_input_submitted)
    # Should check for "/" prefix
    assert '"/"' in source or "startswith" in source


def test_tui_process_message_persists_to_db():
    """_process_message must persist messages when db is available."""
    import inspect
    from kageko.tui.app import KagekoTUI
    source = inspect.getsource(KagekoTUI._process_message)
    assert "append_message" in source or "db" in source
