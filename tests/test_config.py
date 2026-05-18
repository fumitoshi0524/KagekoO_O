from __future__ import annotations

import json
from pathlib import Path

from qaoa.cli.config import load_global_config, save_global_config, get_config_path


def test_get_config_path():
    path = get_config_path()
    assert path.name == "config.json"
    assert ".kageko" in str(path)


def test_load_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = load_global_config()
    assert result == {}


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    kageko_dir = tmp_path / ".kageko"
    kageko_dir.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    config = {"provider": "openai", "api_key": "sk-test", "model": "gpt-4"}
    save_global_config(config)

    loaded = load_global_config()
    assert loaded["provider"] == "openai"
    assert loaded["api_key"] == "sk-test"


def test_load_handles_corrupt_json(tmp_path, monkeypatch):
    kageko_dir = tmp_path / ".kageko"
    kageko_dir.mkdir()
    (kageko_dir / "config.json").write_text("not valid json{{{")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = load_global_config()
    assert result == {}
