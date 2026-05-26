import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clean_kageko_env():
    """Remove any KAGEKO_ env vars after each test (dotenv leaks via os.environ)."""
    yield
    for key in list(os.environ):
        if key.startswith("KAGEKO_"):
            del os.environ[key]


def test_user_env_loaded(tmp_path, monkeypatch):
    user_env = tmp_path / ".kageko"
    user_env.mkdir()
    (user_env / ".env").write_text("KAGEKO_API_KEY=user-key-123\n")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    from kageko.config import load_config
    config = load_config()
    assert config.agent.api_key == "user-key-123"


def test_project_env_fills_missing(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("KAGEKO_MODEL=proj-model\n")
    monkeypatch.chdir(tmp_path)
    from kageko.config import load_config
    config = load_config()
    assert config.agent.model == "proj-model"


def test_user_env_overrides_project(tmp_path, monkeypatch):
    user_env = tmp_path / ".kageko"
    user_env.mkdir()
    (user_env / ".env").write_text("KAGEKO_API_KEY=user-key\n")
    (tmp_path / ".env").write_text("KAGEKO_API_KEY=proj-key\n")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    from kageko.config import load_config
    config = load_config()
    assert config.agent.api_key == "user-key"


def test_no_env_files_no_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    from kageko.config import load_config
    config = load_config()
    assert config.agent.model == "gpt-4o"
