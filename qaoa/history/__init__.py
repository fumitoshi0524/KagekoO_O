"""History management for Kageko.

This module provides conversation history management, including
automatic summarization for long conversations.

Example usage:
    from qaoa.history import Summarizer, SummarizerService

    # Direct usage
    summarizer = Summarizer(provider, message_service, session_service)
    if await summarizer.should_summarize(session, messages):
        result = await summarizer.summarize(session_id, messages)

    # High-level service
    service = SummarizerService(settings, message_service, session_service)
    result = await service.maybe_summarize(session_id, messages)
"""

from .summarizer import (
    Summarizer,
    SummarizerConfig,
    SummarizerService,
    SummaryResult,
    DEFAULT_MAX_CONTEXT_RATIO,
    DEFAULT_MIN_MESSAGES_TO_SUMMARIZE,
    DEFAULT_SUMMARY_PREFIX,
)
from .diff import get_changes_for_session, format_diff, get_current_file_content

__all__ = [
    "Summarizer",
    "SummarizerConfig",
    "SummarizerService",
    "SummaryResult",
    "DEFAULT_MAX_CONTEXT_RATIO",
    "DEFAULT_MIN_MESSAGES_TO_SUMMARIZE",
    "DEFAULT_SUMMARY_PREFIX",
    "get_changes_for_session",
    "format_diff",
    "get_current_file_content",
]
