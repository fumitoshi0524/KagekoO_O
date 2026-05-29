"""Provider profiles for multi-model support."""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from enum import Enum


class AuthType(str, Enum):
    API_KEY = "api_key"
    OAUTH_DEVICE = "oauth_device"
    NONE = "none"


@dataclass
class ModelInfo:
    name: str
    context_window: int = 8000
    max_output: int = 4096
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_temperature: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class ProviderProfile:
    name: str
    base_url: str = "https://api.openai.com/v1"
    auth_type: AuthType = AuthType.API_KEY
    api_key_env: str = ""
    api_key: str = ""
    models: list[ModelInfo] = field(default_factory=list)
    default_model: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    strip_system_role: bool = False
    tool_choice_format: str = "auto"
    max_retries: int = 3


PROVIDER_PRESETS: dict[str, ProviderProfile] = {
    "openai": ProviderProfile(
        name="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
        models=[
            ModelInfo("gpt-4o", 128000, 16384),
            ModelInfo("gpt-4o-mini", 128000, 16384, cost_per_1k_input=0.15),
        ],
    ),
    "deepseek": ProviderProfile(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        models=[
            ModelInfo("deepseek-chat", 64000, 8192),
            ModelInfo("deepseek-reasoner", 64000, 8192, supports_tools=False, supports_temperature=False),
        ],
    ),
    "ollama": ProviderProfile(
        name="ollama",
        base_url="http://localhost:11434/v1",
        auth_type=AuthType.NONE,
        default_model="llama3",
        models=[ModelInfo("llama3", 8000, 4096)],
    ),
}


def resolve_provider(name: str, config_overrides: dict | None = None) -> ProviderProfile:
    """Get a provider profile, merging preset with config overrides."""
    preset = PROVIDER_PRESETS.get(name)
    if preset is None:
        # Create a minimal profile for unknown providers
        preset = ProviderProfile(name=name)
    else:
        # Copy so we don't mutate the global preset
        preset = copy.deepcopy(preset)
    # Apply overrides
    if config_overrides:
        if "base_url" in config_overrides:
            preset.base_url = config_overrides["base_url"]
        if "api_key_env" in config_overrides:
            preset.api_key_env = config_overrides["api_key_env"]
        if "api_key" in config_overrides:
            preset.api_key = config_overrides["api_key"]
        if "default_model" in config_overrides:
            preset.default_model = config_overrides["default_model"]
    # Resolve API key from env
    if preset.api_key_env and not preset.api_key:
        preset.api_key = os.environ.get(preset.api_key_env, "")
    return preset


def get_model_info(profile: ProviderProfile, model_name: str) -> ModelInfo | None:
    """Look up model info within a provider profile."""
    for m in profile.models:
        if m.name == model_name:
            return m
    return None
