# tests/unit/test_config.py
import pytest
import tempfile
from pathlib import Path
from kageko.config import KagekoConfig, load_config


def test_default_config():
    config = KagekoConfig()
    assert config.agent.model == "gpt-4o"
    assert config.agent.mode == "tool-use"
    assert config.security.mode == "interactive"


def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "kageko.toml"
    cfg_file.write_text("""
[agent]
model = "deepseek-chat"
mode = "qaoa"
max_turns = 50

[security]
mode = "read-only"

[database]
path = "/tmp/test.db"
""")
    config = load_config(str(cfg_file))
    assert config.agent.model == "deepseek-chat"
    assert config.agent.mode == "qaoa"
    assert config.agent.max_turns == 50
    assert config.security.mode == "read-only"


def test_load_config_file_not_found():
    config = load_config("/nonexistent/kageko.toml")
    assert config.agent.model == "gpt-4o"
