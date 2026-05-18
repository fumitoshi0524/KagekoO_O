# QAOA category: search, domain: technology
"""Auxiliary LLM utilities for browser/web content processing.

Kageko already has a unified provider abstraction (``create_provider`` +
``BaseProvider.send_messages``), so we adapt a small subset here.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Optional

from ...providers import create_provider, resolve_provider_from_model
from ....config.settings import get_settings


@dataclass
class _AuxMessage:
    content: str


@dataclass
class _AuxChoice:
    message: _AuxMessage


@dataclass
class AuxiliaryLLMResponse:
    """Small OpenAI-compatible-ish wrapper used by browser/web utils.

    Existing code expects ``response.choices[0].message.content``.
    """

    choices: list[_AuxChoice]
    model: str = ""


def _get_aux_model_from_env() -> Optional[str]:
    # Keep env var names for compatibility with the migrated code.
    model = os.getenv("AUXILIARY_WEB_EXTRACT_MODEL", "").strip()
    if model:
        return model
    return None


def _resolve_provider_for_model(model_id: str) -> tuple[str, str, Any]:
    settings = get_settings()
    provider_name, provider_key = resolve_provider_from_model(
        model_id,
        settings,
        agent_config=None,
    )
    provider_cfg = settings.providers.get(provider_key)
    api_key = getattr(provider_cfg, "api_key", None) if provider_cfg else None
    base_url = getattr(provider_cfg, "base_url", None) if provider_cfg else None
    return provider_name, provider_key, (api_key, base_url)


async def async_call_llm(
    *,
    task: str | None = None,  # kept for signature compatibility
    messages: list[dict[str, Any]],
    temperature: float = 0.1,
    max_tokens: int = 4096,
    model: str | None = None,
    **kwargs: Any,
) -> AuxiliaryLLMResponse:
    """Call an auxiliary LLM for summarization/extraction (non-tool).

    Notes:
    - We intentionally do *not* support tools here; migrated browser/web
      utilities only need plain text extraction.
    - ``task`` is ignored; it exists because upstream call_llm/async_call_llm
      signatures carry it.
    """

    del task, kwargs

    model_id = (model or _get_aux_model_from_env() or "").strip()
    if not model_id:
        raise RuntimeError("Auxiliary LLM model is not configured (model is empty).")

    provider_name, _, (api_key, base_url) = _resolve_provider_for_model(model_id)
    provider = create_provider(
        provider_name=provider_name,
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
        max_tokens=max_tokens,
        system_message="",
    )

    resp = await provider.send_messages(messages=messages, tools=None)
    content = (resp.content or "").strip()
    return AuxiliaryLLMResponse(
        choices=[_AuxChoice(message=_AuxMessage(content=content))],
        model=model_id,
    )


async def check_auxiliary_model(model: str | None = None) -> bool:
    """Best-effort availability check without making a request."""

    model_id = (model or _get_aux_model_from_env() or "").strip()
    if not model_id:
        return False
    try:
        provider_name, _, (api_key, base_url) = _resolve_provider_for_model(model_id)
        _ = create_provider(
            provider_name=provider_name,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
        )
        return True
    except Exception:
        return False


def _run_coro_from_sync(coro):
    """Run an async coroutine from sync context."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Avoid deadlocks in event-loop contexts by using a dedicated thread.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(lambda: asyncio.run(coro))
            return fut.result()
    return asyncio.run(coro)


def call_llm(
    *,
    task: str | None = None,
    messages: list[dict[str, Any]],
    temperature: float = 0.1,
    max_tokens: int = 4096,
    model: str | None = None,
    **kwargs: Any,
) -> AuxiliaryLLMResponse:
    """Sync wrapper for ``async_call_llm`` (used by migrated browser code)."""

    return _run_coro_from_sync(
        async_call_llm(
            task=task,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            **kwargs,
        )
    )
