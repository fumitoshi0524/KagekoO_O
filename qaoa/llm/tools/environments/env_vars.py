# QAOA category: system, domain: technology
"""Strip provider / messaging secrets from subprocess environments (Kageko-aligned subset)."""

from __future__ import annotations

from typing import Final

# Legacy third-party env key for Git Bash path; prefer ``KAAGEKO_GIT_BASH_PATH``.
_LEGACY_GIT_BASH_ENV_KEY: Final[str] = "".join(("H", "E", "R", "M", "E", "S", "_GIT_BASH_PATH"))

# Vars that should not leak into generic shell subprocesses.
_SUBPROCESS_ENV_BLOCKLIST: frozenset[str] = frozenset(
    {
        "OPENAI_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_API_BASE",
        "OPENAI_ORG_ID",
        "OPENAI_ORGANIZATION",
        "OPENROUTER_API_KEY",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "GOOGLE_API_KEY",
        "DEEPSEEK_API_KEY",
        "MISTRAL_API_KEY",
        "GROQ_API_KEY",
        "TOGETHER_API_KEY",
        "PERPLEXITY_API_KEY",
        "COHERE_API_KEY",
        "FIREWORKS_API_KEY",
        "XAI_API_KEY",
        "HELICONE_API_KEY",
        "PARALLEL_API_KEY",
        "FIRECRAWL_API_KEY",
        "FIRECRAWL_API_URL",
        "MODAL_TOKEN_ID",
        "MODAL_TOKEN_SECRET",
        "DAYTONA_API_KEY",
        "GH_TOKEN",
        "GITHUB_APP_ID",
        "GITHUB_APP_PRIVATE_KEY_PATH",
        "GITHUB_APP_INSTALLATION_ID",
        "LLM_MODEL",
    }
)

_FORCE_PREFIX: Final = "_KAAGEKO_FORCE_"


def sanitize_subprocess_env(
    base_env: dict[str, str] | None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Filter blocked keys; ``_KAAGEKO_FORCE_<NAME>`` opts a variable back in."""
    sanitized: dict[str, str] = {}

    for key, value in (base_env or {}).items():
        if key.startswith(_FORCE_PREFIX):
            continue
        if key not in _SUBPROCESS_ENV_BLOCKLIST:
            sanitized[key] = value

    for key, value in (extra_env or {}).items():
        if key.startswith(_FORCE_PREFIX):
            real_key = key[len(_FORCE_PREFIX):]
            sanitized[real_key] = value
        elif key not in _SUBPROCESS_ENV_BLOCKLIST:
            sanitized[key] = value

    return sanitized


def merge_run_env(
    base: dict[str, str] | None,
    extra: dict[str, str] | None,
) -> dict[str, str]:
    """``os.environ`` merged with instance env, then sanitized."""
    import os

    merged = dict(os.environ)
    merged.update(base or {})
    merged.update(extra or {})
    return sanitize_subprocess_env(merged, None)
