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


def test_config_context_window_size():
    from kageko.config import load_config
    config = load_config()
    assert hasattr(config.agent, "context_window_size")
    assert config.agent.context_window_size == 8000

def test_config_temperature():
    from kageko.config import load_config
    config = load_config()
    assert hasattr(config.agent, "temperature")
    assert config.agent.temperature == 0.7

def test_load_config_custom_temperature_and_context_window(tmp_path):
    cfg_file = tmp_path / "kageko.toml"
    cfg_file.write_text("""
[agent]
model = "gpt-4o"
temperature = 0.3
context_window_size = 16000
""")
    config = load_config(str(cfg_file))
    assert config.agent.temperature == 0.3
    assert config.agent.context_window_size == 16000


def test_config_env_var_override_api_key():
    import os
    from kageko.config import load_config
    os.environ["KAGEKO_API_KEY"] = "test-key-123"
    try:
        config = load_config()
        assert config.agent.api_key == "test-key-123"
    finally:
        del os.environ["KAGEKO_API_KEY"]

def test_config_env_var_override_model():
    import os
    from kageko.config import load_config
    os.environ["KAGEKO_MODEL"] = "gpt-3.5-turbo"
    try:
        config = load_config()
        assert config.agent.model == "gpt-3.5-turbo"
    finally:
        del os.environ["KAGEKO_MODEL"]

def test_config_env_var_override_base_url():
    import os
    from kageko.config import load_config
    os.environ["KAGEKO_BASE_URL"] = "http://localhost:8080/v1"
    try:
        config = load_config()
        assert config.agent.base_url == "http://localhost:8080/v1"
    finally:
        del os.environ["KAGEKO_BASE_URL"]


def test_provider_config(tmp_path):
    toml = """
[providers.openai]
base_url = "https://api.openai.com/v1"
api_key = "sk-test"

[agent]
provider = "openai"
model = "gpt-4o"
"""
    (tmp_path / "k.toml").write_text(toml)
    from kageko.config import load_config
    config = load_config(str(tmp_path / "k.toml"))
    assert config.agent.base_url == "https://api.openai.com/v1"
    assert config.agent.api_key == "sk-test"

def test_provider_api_key_env(tmp_path, monkeypatch):
    toml = """
[providers.local]
base_url = "http://localhost:8080/v1"
api_key_env = "LOCAL_KEY"

[agent]
provider = "local"
"""
    monkeypatch.setenv("LOCAL_KEY", "env-resolved-key")
    (tmp_path / "k.toml").write_text(toml)
    from kageko.config import load_config
    config = load_config(str(tmp_path / "k.toml"))
    assert config.agent.api_key == "env-resolved-key"

def test_provider_backward_compat(tmp_path):
    toml = '[agent]\nmodel = "gpt-4o"\napi_key = "flat-key"\n'
    (tmp_path / "k.toml").write_text(toml)
    from kageko.config import load_config
    config = load_config(str(tmp_path / "k.toml"))
    assert config.agent.api_key == "flat-key"

def test_provider_unknown_falls_back(tmp_path):
    toml = '[agent]\nprovider = "nonexistent"\n'
    (tmp_path / "k.toml").write_text(toml)
    from kageko.config import load_config
    config = load_config(str(tmp_path / "k.toml"))
    assert config.agent.base_url == "https://api.openai.com/v1"
