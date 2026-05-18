"""LLM providers.

This module exposes provider implementations and helpers for creating
providers from configuration.

Kageko supports custom ``base_url`` + ``api_key`` for OpenAI/Anthropic-compatible APIs.
Different endpoints can be configured via multiple keys in ``Settings.providers``
(e.g. ``openai_compat``, ``claude_proxy``).
"""

# QAOA turn: maps to QAOAAction

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

# NOTE: provider modules are imported lazily in `create_provider` to keep
# startup fast (some providers pull in heavy deps).
from ..base import BaseProvider, CacheStats, TokenUsage

if TYPE_CHECKING:
    from ...config.settings import Settings, AgentConfig

__all__ = [
    "BaseProvider",
    "CacheStats",
    "TokenUsage",
    "create_provider",
    "list_providers",
    "resolve_provider_from_model",
]


def list_providers() -> list[str]:
    """List all available provider names.

    Returns:
        List of provider names
    """
    return [
        "anthropic",
        "openai",
        "gemini",
        "groq",
        "azure",
        "openrouter",
        "xai",
        "bedrock",
        "copilot",
    ]


def resolve_provider_from_model(
    model: str,
    settings: "Settings",
    agent_config: "AgentConfig | None" = None,
) -> tuple[str, str]:
    """Resolve provider name and provider_key from model & settings.

    This helper allows users to define multiple config slots for the same provider
    type (e.g. ``openai`` and ``openai_compat``) and select one via AgentConfig
    ``provider_key``.
    Args:
        model: Model identifier (e.g. ``gpt-4o`` / ``claude-3-5-sonnet-20241022``).
        settings: Global Settings instance (contains ``providers`` mapping).
        agent_config: Optional agent config (contains ``provider_key``).

    Returns:
        (provider_name, provider_key)
    """
    model_lower = (model or "").lower()

    # Claude compatible gateways often use ``anthropic/<model>`` (Messages API).
    if (
        "/" in model_lower
        and not model_lower.startswith("http")
        and model_lower.count("/") == 1
        and model_lower.startswith("anthropic/")
    ):
        provider_name = "anthropic"
    # DashScope compatible gateway ``dashscope/<id>`` form.
    elif (
        "/" in model_lower
        and not model_lower.startswith("http")
        and model_lower.count("/") == 1
        and model_lower.startswith("dashscope/")
    ):
        provider_name = "openai"
    # MiniMax compatible gateway ``minimax/<id>`` form.
    elif (
        "/" in model_lower
        and not model_lower.startswith("http")
        and model_lower.count("/") == 1
        and model_lower.startswith("minimax/")
    ):
        provider_name = "openai"
    # Volcengine compatible gateway ``volcengine/<id>`` form.
    elif (
        "/" in model_lower
        and not model_lower.startswith("http")
        and model_lower.count("/") == 1
        and model_lower.startswith("volcengine/")
    ):
        provider_name = "openai"
    # OpenRouter-style ids: ``vendor/model`` (single segment slash). Must run before
    # ``gpt`` / ``llama`` substring rules (e.g. ``openai/gpt-4o``, ``meta-llama/...``).
    elif (
        "/" in model_lower
        and not model_lower.startswith("http")
        and model_lower.count("/") == 1
    ):
        provider_name = "openrouter"
    # Basic provider type inference
    elif "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
        provider_name = "openai"
    elif model_lower.startswith("claude-") or "claude" in model_lower or "anthropic" in model_lower:
        provider_name = "anthropic"
    elif "gemini" in model_lower:
        provider_name = "gemini"
    elif "groq" in model_lower or "llama" in model_lower or "mixtral" in model_lower:
        provider_name = "groq"
    elif "deepseek" in model_lower:
        provider_name = "openai"
    elif "grok" in model_lower:
        provider_name = "xai"
    elif (
        "moonshot" in model_lower
        or model_lower.startswith("kimi-")
        or model_lower.startswith("kimi-k2")
    ):
        provider_name = "openai"
    elif model_lower.startswith("mistral-") or "pixtral" in model_lower or "codestral" in model_lower:
        provider_name = "openai"
    elif (
        "qwen" in model_lower
        or "dashscope" in model_lower
        or model_lower.startswith("qwq")
        or model_lower.startswith("qvq")
    ):
        provider_name = "openai"
    elif "minimax" in model_lower or model_lower.startswith("abab"):
        provider_name = "openai"
    elif model_lower.startswith("doubao-") or model_lower.startswith("ep-"):
        provider_name = "openai"
    elif model_lower.startswith("command-r") or "command-a" in model_lower or "cohere" in model_lower:
        provider_name = "openai"
    elif "glm-" in model_lower or model_lower.startswith("glm"):
        provider_name = "openai"
    else:
        # Default fallback to Anthropic to preserve existing behavior.
        provider_name = "anthropic"

    # Prefer explicit provider_key from agent config.
    explicit_key = getattr(agent_config, "provider_key", None) if agent_config else None
    if explicit_key and explicit_key in settings.providers:
        provider_key = explicit_key
        # If key looks like an OpenAI-compatible slot, treat as openai provider.
        lk = explicit_key.lower()
        if lk in ("groq", "openrouter", "xai", "bedrock", "copilot"):
            provider_name = lk
        elif "openai" in lk and "anthropic" not in lk:
            provider_name = "openai"
        elif "anthropic" in lk and "openai" not in lk:
            provider_name = "anthropic"
    else:
        # Default to same-name slot (e.g. "openai" / "anthropic") when present.
        if provider_name in settings.providers:
            provider_key = provider_name
        else:
            # If user only configured custom keys, try first key with same prefix.
            fallback_key = None
            for key in settings.providers.keys():
                if key.startswith(provider_name):
                    fallback_key = key
                    break
            provider_key = fallback_key or provider_name

    return provider_name, provider_key


def create_provider(
    provider_name: str,
    model_id: str,
    api_key: str | None = None,
    **kwargs,
) -> BaseProvider:
    """Create a provider instance.

    Args:
        provider_name: Provider type (anthropic, openai, gemini, groq, azure, openrouter, xai, bedrock, copilot)
        model_id: Model identifier
        api_key: API key
        **kwargs: Additional provider-specific arguments

    Returns:
        Provider instance

    Raises:
        ValueError: If provider name is unknown
    """
    def _load_factory(name: str) -> Callable[..., BaseProvider]:
        if name == "anthropic":
            from .anthropic import create_anthropic_provider

            return create_anthropic_provider
        if name == "openai":
            from .openai import create_openai_provider

            return create_openai_provider
        if name == "gemini":
            from .gemini import create_gemini_provider

            return create_gemini_provider
        if name == "groq":
            from .groq import create_groq_provider

            return create_groq_provider
        if name == "azure":
            from .azure import create_azure_provider

            return create_azure_provider
        if name == "openrouter":
            from .openrouter import create_openrouter_provider

            return create_openrouter_provider
        if name == "xai":
            from .xai import create_xai_provider

            return create_xai_provider
        if name == "bedrock":
            from .bedrock import create_bedrock_provider

            return create_bedrock_provider
        if name == "copilot":
            from .copilot import create_copilot_provider

            return create_copilot_provider
        raise ValueError(
            f"Unknown provider: {name}. Available: {list_providers()}"
        )

    factory = _load_factory(provider_name)
    if provider_name == "anthropic":
        if not (api_key and str(api_key).strip()):
            from .anthropic import _resolve_anthropic_token

            api_key = _resolve_anthropic_token()
    return factory(model=model_id, api_key=api_key, **kwargs)
