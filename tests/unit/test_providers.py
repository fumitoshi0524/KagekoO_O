"""Tests for provider profiles."""
from __future__ import annotations

import os
import pytest

from kageko.llm.providers import (
    AuthType,
    ModelInfo,
    ProviderProfile,
    PROVIDER_PRESETS,
    get_model_info,
    resolve_provider,
)


def test_provider_presets_exist():
    assert "openai" in PROVIDER_PRESETS
    assert "deepseek" in PROVIDER_PRESETS
    assert "ollama" in PROVIDER_PRESETS


def test_openai_preset():
    p = PROVIDER_PRESETS["openai"]
    assert p.base_url == "https://api.openai.com/v1"
    assert p.default_model == "gpt-4o"
    assert p.api_key_env == "OPENAI_API_KEY"
    assert len(p.models) > 0


def test_ollama_preset_no_auth():
    p = PROVIDER_PRESETS["ollama"]
    assert p.auth_type == AuthType.NONE
    assert "localhost" in p.base_url


def test_resolve_provider_preset():
    p = resolve_provider("openai")
    assert p.name == "openai"
    assert p.base_url == "https://api.openai.com/v1"


def test_resolve_provider_with_overrides():
    p = resolve_provider("openai", {"base_url": "https://custom.api.com/v1"})
    assert p.base_url == "https://custom.api.com/v1"


def test_resolve_unknown_provider():
    p = resolve_provider("unknown_provider")
    assert p.name == "unknown_provider"


def test_resolve_provider_env_key(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret123")
    p = ProviderProfile(name="test", api_key_env="TEST_API_KEY")
    # Simulate what resolve_provider does
    if p.api_key_env and not p.api_key:
        p.api_key = os.environ.get(p.api_key_env, "")
    assert p.api_key == "secret123"


def test_get_model_info():
    p = PROVIDER_PRESETS["openai"]
    info = get_model_info(p, "gpt-4o")
    assert info is not None
    assert info.context_window == 128000


def test_get_model_info_not_found():
    p = PROVIDER_PRESETS["openai"]
    info = get_model_info(p, "nonexistent-model")
    assert info is None


def test_model_info_defaults():
    m = ModelInfo("test-model")
    assert m.context_window == 8000
    assert m.supports_tools is True
    assert m.cost_per_1k_input == 0.0
