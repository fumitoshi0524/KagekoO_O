# QAOA: UniToolCall adapter registry
"""OpenAI-compatible vendor adapters."""

from .adapter import AdapterContext, OpenAICompatAdapter, select_openai_compat_adapter

__all__ = [
    "AdapterContext",
    "OpenAICompatAdapter",
    "select_openai_compat_adapter",
]
