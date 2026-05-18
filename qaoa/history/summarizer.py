"""Session summarization service for Kageko.

This module provides automatic conversation summarization when conversations
become too long, helping to manage context window limits and reduce token usage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..config.constants import AgentName, CONTEXT_WINDOWS
from ..config.settings import Settings, get_settings
from ..llm.base import BaseProvider, ProviderResponse

if TYPE_CHECKING:
    from ..llm.providers import AnthropicProvider

logger = logging.getLogger(__name__)

# Token heuristics undercount vs provider tokenizers (especially code/JSON).
# Use extra headroom to stay under strict context limits.
_SUMMARY_INPUT_SAFETY_RATIO = 0.62
_SUMMARY_PROMPT_OVERHEAD_TOKENS = 3200
_SUMMARY_CHUNK_FRACTION = 0.42


# Default summarization thresholds
DEFAULT_MAX_CONTEXT_RATIO = 0.7  # Summarize when 70% of context window is used
DEFAULT_MIN_MESSAGES_TO_SUMMARIZE = 10  # Minimum messages before summarization
DEFAULT_SUMMARY_PREFIX = "[SUMMARY] "  # Prefix for summary messages


# ---------------------------------------------------------------------------
# Compatibility types (adapt to qaoa's message/session modules)
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """Compatibility wrapper for qaoa message records."""

    id: str
    role: str
    content: str
    thinking: str = ""
    session_id: str = ""


class MessageService:
    """Compatibility adapter for qaoa message storage."""

    def __init__(self, db: Any = None) -> None:
        from ..db.connection import get_database as _get_db
        self._db = db or _get_db()

    async def create(self, session_id: str, role: str, content: str) -> Message:
        import uuid
        msg = Message(
            id=uuid.uuid4().hex[:12],
            role=str(role),
            content=content,
            session_id=session_id,
        )
        self._db.append("messages", {
            "id": msg.id, "role": msg.role,
            "content": msg.content, "thinking": msg.thinking,
            "session_id": msg.session_id,
        })
        return msg

    async def list_by_session(self, session_id: str) -> list[Message]:
        raw = self._db.read_where("messages", key="session_id", value=session_id)
        return [Message(
            id=r.get("id", ""), role=r.get("role", "user"),
            content=r.get("content", ""), thinking=r.get("thinking", ""),
            session_id=session_id,
        ) for r in raw]


@dataclass
class Session:
    """Compatibility adapter for qaoa session records."""

    id: str
    summary_message_id: str = ""
    title: str = ""


class SessionService:
    """Compatibility adapter for qaoa session storage."""

    def __init__(self, db: Any = None) -> None:
        from ..db.connection import get_database as _get_db
        self._db = db or _get_db()

    async def get(self, session_id: str) -> Session | None:
        rows = self._db.read_where("sessions", key="id", value=session_id)
        if not rows:
            return None
        r = rows[0]
        return Session(
            id=r.get("id", ""),
            summary_message_id=r.get("summary_message_id", ""),
            title=r.get("title", ""),
        )

    async def update(self, session: Session) -> None:
        self._db.update_where(
            "sessions", key="id", value=session.id,
            updates={"summary_message_id": session.summary_message_id},
        )


# ---------------------------------------------------------------------------
# Summarizer types
# ---------------------------------------------------------------------------


@dataclass
class SummaryResult:
    """Result of a summarization operation.

    Attributes:
        summary_message: The generated summary message
        messages_summarized: Number of messages that were summarized
        tokens_saved: Estimated tokens saved by summarization
        original_tokens: Estimated tokens in the original messages
    """

    summary_message: Message
    messages_summarized: int
    tokens_saved: int
    original_tokens: int

    @property
    def compression_ratio(self) -> float:
        """Calculate the compression ratio.

        Returns:
            Ratio of tokens saved to original tokens
        """
        if self.original_tokens == 0:
            return 0.0
        return self.tokens_saved / self.original_tokens


@dataclass
class SummarizerConfig:
    """Configuration for the summarizer.

    Attributes:
        max_context_ratio: Ratio of context window at which to trigger summarization
        min_messages: Minimum messages before considering summarization
        keep_recent_messages: Number of recent messages to keep unsummarized
        max_summary_tokens: Maximum tokens for the summary
        enabled: Whether auto-summarization is enabled
    """

    max_context_ratio: float = DEFAULT_MAX_CONTEXT_RATIO
    min_messages: int = DEFAULT_MIN_MESSAGES_TO_SUMMARIZE
    keep_recent_messages: int = 4
    max_summary_tokens: int = 4096
    enabled: bool = True


class Summarizer:
    """Service for generating conversation summaries.

    The Summarizer automatically generates summaries of conversations when they
    become too long, helping to manage context window limits and reduce token usage.

    Usage:
        summarizer = Summarizer(provider, message_service, session_service)

        # Check if summarization is needed
        if await summarizer.should_summarize(session, messages):
            result = await summarizer.summarize(session_id, messages)
            print(f"Saved {result.tokens_saved} tokens")
    """

    def __init__(
        self,
        provider: BaseProvider,
        message_service: MessageService,
        session_service: SessionService,
        config: SummarizerConfig | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the summarizer.

        Args:
            provider: LLM provider for generating summaries
            message_service: Message service for creating summary messages
            session_service: Session service for updating session metadata
            config: Summarizer configuration
            settings: Application settings
        """
        self._provider = provider
        self._message_service = message_service
        self._session_service = session_service
        self._config = config or SummarizerConfig()
        self._settings = settings

        # System prompt for summarization
        self._system_prompt = self._get_summarizer_prompt()

    def _get_summarizer_prompt(self) -> str:
        """Get the system prompt for summarization.

        Returns:
            System prompt string
        """
        return """You are a helpful AI assistant tasked with summarizing conversations.

When asked to summarize, provide a detailed but concise summary of the conversation.
Focus on information that would be helpful for continuing the conversation, including:
- What was done
- What is currently being worked on
- Which files are being modified
- What needs to be done next

Your summary should be comprehensive enough to provide context but concise enough to be quickly understood.

Format your summary as follows:
1. Overview (1-2 sentences describing the main goal)
2. Key Points (bullet points of important details)
3. Current State (what is happening now)
4. Next Steps (if any)

Keep the summary focused on technical details, code changes, and decisions made."""

    def _get_context_window(self, model: str) -> int:
        """Get the context window size for a model.

        Args:
            model: Model identifier

        Returns:
            Context window size in tokens
        """
        # Check known context windows
        for model_prefix, window in CONTEXT_WINDOWS.items():
            if model.startswith(model_prefix) or model_prefix in model:
                return window

        # Default to 128k for unknown models
        return 128000

    def _completion_reserve_tokens(self) -> int:
        """Return reserved completion tokens for the active provider."""
        raw = getattr(self._provider, "max_tokens", 0)
        try:
            val = int(raw or 0)
        except Exception:
            val = 0
        # Keep a practical minimum reserve so strict APIs don't reject
        # requests where messages + completion exceed total context.
        return max(1024, val)

    def _estimate_tokens(self, messages: list[Message]) -> int:
        """Estimate the token count for a list of messages.

        Uses a simple heuristic of ~4 characters per token.

        Args:
            messages: List of messages to estimate

        Returns:
            Estimated token count
        """
        total_chars = 0
        for msg in messages:
            # Count content characters
            total_chars += len(msg.content)
            # Count thinking content
            total_chars += len(msg.thinking)
            # Add overhead for message structure
            total_chars += 50  # Role, metadata, etc.

        # Rough estimate: 4 characters per token
        return total_chars // 4

    @staticmethod
    def _response_text(response: ProviderResponse) -> str:
        """Extract assistant text from provider response (compat gateways may fill thinking only)."""
        c = (response.content or "").strip()
        if c:
            return response.content
        t = (getattr(response, "thinking", None) or "").strip()
        return t or ""

    def _message_weight_tokens(self, msg: Message) -> int:
        """Pessimistic per-message weight for summary budgeting (vs provider counts)."""
        return max(1, int(self._estimate_tokens([msg]) * 1.38) + 120)

    def _truncate_for_summary_budget(
        self, messages: list[Message], max_weight_tokens: int
    ) -> list[Message]:
        """Keep newest messages within pessimistic token budget."""
        if not messages or max_weight_tokens <= 0:
            return []
        result: list[Message] = []
        total = 0
        for msg in reversed(messages):
            w = self._message_weight_tokens(msg)
            if total + w > max_weight_tokens:
                break
            result.insert(0, msg)
            total += w
        return result

    def _heuristic_summary_text(
        self,
        messages: list[Message],
        *,
        max_items: int = 56,
        snippet: int = 420,
    ) -> str:
        """Lossy fallback summary when LLM fails/returns empty (still enables /compact)."""
        if not messages:
            return ""
        header = (
            "[Heuristic compact - LLM summary unavailable/empty/rejected. "
            "Below are short excerpts from archived turns; recent messages remain preserved.]\n\n"
        )
        lines = [header]
        for msg in messages[-max_items:]:
            role = str(msg.role).upper()
            body = (msg.content or "").strip()
            if not body and (msg.thinking or "").strip():
                body = f"_(thinking)_ {(msg.thinking or '')[:180]}"
            if len(body) > snippet:
                body = body[:snippet] + "..."
            lines.append(f"- **{role}:** {body or '_(no plain text)_'}")
        return "\n".join(lines)

    async def should_summarize(
        self,
        session: Session,
        messages: list[Message],
        model: str | None = None,
    ) -> bool:
        """Check if a session should be summarized.

        Args:
            session: The session to check
            messages: Current messages in the session
            model: Model being used (for context window calculation)

        Returns:
            True if summarization should be performed
        """
        # Check if auto-summarization is enabled
        if not self._config.enabled:
            return False

        # Check settings for auto_compact
        if self._settings and not self._settings.auto_compact:
            return False

        # Check minimum message count
        if len(messages) < self._config.min_messages:
            return False

        # Check if already summarized recently
        if session.summary_message_id:
            # Find the summary message index
            for i, msg in enumerate(messages):
                if msg.id == session.summary_message_id:
                    # Only count messages after the summary
                    messages_after_summary = messages[i + 1 :]
                    if len(messages_after_summary) < self._config.min_messages:
                        return False
                    break

        # Get context window for the model and keep headroom for completion.
        context_window = self._get_context_window(model or "default")
        completion_reserve = self._completion_reserve_tokens()
        safety_margin = max(1024, int(context_window * 0.02))
        prompt_budget = max(4096, context_window - completion_reserve - safety_margin)
        threshold = int(prompt_budget * self._config.max_context_ratio)

        # Estimate current token usage
        current_tokens = self._estimate_tokens(messages)

        logger.debug(
            "Summarization check: %s/%s tokens (%s messages), "
            "window=%s reserve=%s margin=%s budget=%s",
            current_tokens,
            threshold,
            len(messages),
            context_window,
            completion_reserve,
            safety_margin,
            prompt_budget,
        )

        return current_tokens >= threshold

    async def summarize(
        self,
        session_id: str,
        messages: list[Message],
        keep_recent: int | None = None,
        extra_user_instructions: str = "",
    ) -> SummaryResult | None:
        """Generate a summary of the conversation.

        Args:
            session_id: Session ID
            messages: QAOA turns to summarize
            keep_recent: Number of recent messages to keep (overrides config)

        Returns:
            SummaryResult if successful, None otherwise
        """
        if not messages:
            return None

        keep_recent = keep_recent or self._config.keep_recent_messages

        # Determine which messages to summarize
        if len(messages) <= keep_recent:
            logger.warning("Not enough messages to summarize after keeping recent ones")
            return None

        messages_to_summarize = messages[:-keep_recent]

        # Estimate original tokens
        original_tokens = self._estimate_tokens(messages_to_summarize)

        # Keep the summarization prompt under strict context limits.
        provider_model = getattr(self._provider, "model", None) or getattr(
            self._provider, "model_id", None
        )
        context_window = self._get_context_window(str(provider_model or "default"))
        completion_reserve = self._completion_reserve_tokens()
        safety_margin = max(1024, int(context_window * 0.02))
        raw_prompt_ceiling = max(
            4096,
            context_window
            - completion_reserve
            - safety_margin
            - self._config.max_summary_tokens
            - _SUMMARY_PROMPT_OVERHEAD_TOKENS,
        )
        prompt_budget = max(4096, int(raw_prompt_ceiling * _SUMMARY_INPUT_SAFETY_RATIO))

        messages_to_summarize = self._truncate_for_summary_budget(
            messages_to_summarize, prompt_budget
        ) or messages_to_summarize

        # Format the conversation for summarization
        conversation_text = self._format_messages_for_summary(messages_to_summarize)

        # Create the summarization request
        summary_request = f"""Please summarize the following conversation. Focus on:
1. The main goal or task
2. Key decisions and changes made
3. Files modified or discussed
4. Any important context for continuing the work

Conversation to summarize:

{conversation_text}"""
        extra = (extra_user_instructions or "").strip()
        if extra:
            summary_request += f"\n\nAdditional instructions from the user:\n{extra}\n"

        def _approx_wire_tokens(system_s: str, user_s: str) -> int:
            # ~3 chars/token is safer than our 4 chars/token heuristic for code/JSON.
            return max(1, int((len(system_s) + len(user_s)) / 3) + 900)

        try:
            summary_text = ""
            if _approx_wire_tokens(self._system_prompt, summary_request) > prompt_budget:
                logger.warning(
                    "Summary request too large; using chunked summarization fallback."
                )
                summary_text = await self._summarize_in_chunks(
                    session_id=session_id,
                    messages_to_summarize=messages_to_summarize,
                    prompt_budget=prompt_budget,
                    extra_user_instructions=extra,
                )
            else:
                response: ProviderResponse = await self._provider.send_messages(
                    messages=[
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": summary_request},
                    ],
                    tools=None,
                )
                summary_text = self._response_text(response)

            summary_text = (summary_text or "").strip()
            if not summary_text:
                logger.error("Empty summary from provider; using heuristic fallback.")
                summary_text = self._heuristic_summary_text(messages_to_summarize)

            if not summary_text.strip():
                return None

            # Create the summary message
            summary_message = await self._message_service.create(
                session_id=session_id,
                role="system",
                content=f"{DEFAULT_SUMMARY_PREFIX}{summary_text}",
            )

            # Estimate tokens saved
            summary_tokens = self._estimate_tokens([summary_message])
            tokens_saved = original_tokens - summary_tokens

            logger.info(
                f"Generated summary: {len(messages_to_summarize)} messages -> "
                f"{tokens_saved} tokens saved"
            )

            return SummaryResult(
                summary_message=summary_message,
                messages_summarized=len(messages_to_summarize),
                tokens_saved=max(0, tokens_saved),
                original_tokens=original_tokens,
            )

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            summary_text = self._heuristic_summary_text(messages_to_summarize)
            if not summary_text.strip():
                return None
            try:
                summary_message = await self._message_service.create(
                    session_id=session_id,
                    role="system",
                    content=f"{DEFAULT_SUMMARY_PREFIX}{summary_text}",
                )
            except Exception as e2:
                logger.error(f"Heuristic summary persistence failed: {e2}")
                return None
            summary_tokens = self._estimate_tokens([summary_message])
            tokens_saved = original_tokens - summary_tokens
            return SummaryResult(
                summary_message=summary_message,
                messages_summarized=len(messages_to_summarize),
                tokens_saved=max(0, tokens_saved),
                original_tokens=original_tokens,
            )

    async def _summarize_in_chunks(
        self,
        *,
        session_id: str,
        messages_to_summarize: list[Message],
        prompt_budget: int,
        extra_user_instructions: str = "",
    ) -> str:
        """Chunked summarization fallback for oversized histories."""
        if not messages_to_summarize:
            return ""

        chunk_msg_budget = max(4500, int(prompt_budget * _SUMMARY_CHUNK_FRACTION))

        chunks: list[list[Message]] = []
        buf: list[Message] = []
        buf_tokens = 0
        for msg in messages_to_summarize:
            t = self._message_weight_tokens(msg)
            if buf and buf_tokens + t > chunk_msg_budget:
                chunks.append(buf)
                buf = []
                buf_tokens = 0
            buf.append(msg)
            buf_tokens += t
        if buf:
            chunks.append(buf)

        running = ""
        running_cap = 9000

        for i, chunk in enumerate(chunks, start=1):
            chunk_text = self._format_messages_for_summary(chunk)
            user_prompt = f"""Summarize this conversation segment.

Segment {i}/{len(chunks)}:

{chunk_text}
"""
            run = (running or "").strip()
            if run:
                if len(run) > running_cap:
                    run = run[:running_cap] + "\n... (truncated)"
                user_prompt = (
                    "We are building a running summary across multiple segments.\n\n"
                    f"Current running summary:\n{run}\n\n"
                    + user_prompt
                )
            extra = (extra_user_instructions or "").strip()
            if extra:
                user_prompt += f"\nAdditional instructions from the user:\n{extra}\n"

            response: ProviderResponse = await self._provider.send_messages(
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=None,
            )
            running = self._response_text(response).strip()
            if not running:
                return ""

        return running

    def _format_messages_for_summary(self, messages: list[Message]) -> str:
        """Format messages for the summarization prompt.

        Args:
            messages: Messages to format

        Returns:
            Formatted conversation string
        """
        lines = []

        for msg in messages:
            role = str(msg.role).upper()
            content = msg.content

            # Truncate very long messages
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"

            lines.append(f"### {role}")
            lines.append(content)
            lines.append("")

            # Include thinking content if present
            if msg.thinking:
                thinking = msg.thinking
                if len(thinking) > 500:
                    thinking = thinking[:500] + "\n... (truncated)"
                lines.append(f"### {role} (thinking)")
                lines.append(thinking)
                lines.append("")

        return "\n".join(lines)

    async def get_context_with_summary(
        self,
        session_id: str,
        messages: list[Message],
        max_tokens: int,
    ) -> list[Message]:
        """Get messages for context, replacing old messages with summary if available.

        This method returns a list of messages suitable for the context window,
        replacing older messages with a summary if one exists.

        Args:
            session_id: Session ID
            messages: All messages in the session
            max_tokens: Maximum tokens for the context

        Returns:
            List of messages for context
        """
        # Get the session to check for existing summary
        session = await self._session_service.get(session_id)

        if not session or not session.summary_message_id:
            # No summary, return messages as-is (with token limit)
            return self._truncate_messages_by_tokens(messages, max_tokens)

        # Find the summary message
        summary_idx = None
        for i, msg in enumerate(messages):
            if msg.id == session.summary_message_id:
                summary_idx = i
                break

        if summary_idx is None:
            # Summary message not found, return as-is
            return self._truncate_messages_by_tokens(messages, max_tokens)

        # Get summary and messages after it
        summary_msg = messages[summary_idx]
        messages_after = messages[summary_idx + 1 :]

        # Combine summary with recent messages
        result = [summary_msg] + messages_after

        return self._truncate_messages_by_tokens(result, max_tokens)

    def _truncate_messages_by_tokens(
        self,
        messages: list[Message],
        max_tokens: int,
    ) -> list[Message]:
        """Truncate messages to fit within token limit.

        Keeps the most recent messages that fit within the limit.

        Args:
            messages: Messages to truncate
            max_tokens: Maximum tokens

        Returns:
            Truncated list of messages
        """
        if not messages:
            return []

        # Start from the most recent and work backwards
        result = []
        total_tokens = 0

        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens([msg])
            if total_tokens + msg_tokens > max_tokens:
                break
            result.insert(0, msg)
            total_tokens += msg_tokens

        return result


class SummarizerService:
    """High-level service for managing conversation summarization.

    This service provides a convenient interface for summarization,
    handling the coordination between sessions, messages, and the summarizer.

    Usage:
        service = SummarizerService(settings, message_service, session_service)

        # Auto-summarize if needed
        result = await service.maybe_summarize(session_id, messages)
    """

    def __init__(
        self,
        settings: Settings,
        message_service: MessageService,
        session_service: SessionService,
        provider: BaseProvider | None = None,
    ) -> None:
        """Initialize the summarizer service.

        Args:
            settings: Application settings
            message_service: Message service
            session_service: Session service
            provider: LLM provider (will be created if not provided)
        """
        self._settings = settings
        self._message_service = message_service
        self._session_service = session_service
        self._provider = provider
        self._summarizer: Summarizer | None = None

    def _get_provider(self) -> BaseProvider:
        """Get or create the LLM provider for summarization.

        Returns:
            LLM provider instance
        """
        if self._provider is not None:
            return self._provider

        # Create provider based on settings (respect agent provider_key slot).
        from ..llm.providers import create_provider, resolve_provider_from_model

        agent_config = self._settings.get_agent_config(AgentName.SUMMARIZER)
        model = agent_config.model
        provider_name, provider_key = resolve_provider_from_model(
            model, self._settings, agent_config
        )

        provider_config = (self._settings.providers or {}).get(provider_key)
        if provider_config is None:
            # Keep behavior consistent: missing slot acts disabled.
            from ..config.settings import Provider as ProviderModel

            provider_config = ProviderModel(disabled=True)

        self._provider = create_provider(
            provider_name=provider_name,
            model_id=model,
            api_key=provider_config.api_key,
            max_tokens=agent_config.max_tokens,
            base_url=getattr(provider_config, "base_url", None),
            timeout=getattr(provider_config, "timeout", 120),
        )
        return self._provider

    def _detect_provider_from_model(self, model: str) -> str:
        """Detect provider name from model identifier.

        Args:
            model: Model identifier

        Returns:
            Provider name string
        """
        model_lower = model.lower()

        if "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
            return "openai"
        elif "gemini" in model_lower:
            return "gemini"
        elif "groq" in model_lower or "llama" in model_lower or "mixtral" in model_lower:
            return "groq"
        elif "azure" in model_lower:
            return "azure"
        elif (
            "moonshot" in model_lower
            or model_lower.startswith("kimi-")
            or model_lower.startswith("kimi-k2")
        ):
            return "openai"
        elif (
            "qwen" in model_lower
            or "dashscope" in model_lower
            or model_lower.startswith("qvq")
            or model_lower.startswith("qwq")
        ):
            return "openai"
        elif "minimax" in model_lower or model_lower.startswith("abab"):
            return "openai"
        elif model_lower.startswith("doubao-") or model_lower.startswith("ep-"):
            return "openai"
        else:
            # Default to anthropic
            return "anthropic"

    def _get_summarizer(self) -> Summarizer:
        """Get or create the summarizer instance.

        Returns:
            Summarizer instance
        """
        if self._summarizer is None:
            self._summarizer = Summarizer(
                provider=self._get_provider(),
                message_service=self._message_service,
                session_service=self._session_service,
                settings=self._settings,
            )
        return self._summarizer

    async def maybe_summarize(
        self,
        session_id: str,
        messages: list[Message],
        model: str | None = None,
    ) -> SummaryResult | None:
        """Summarize the conversation if needed.

        Args:
            session_id: Session ID
            messages: Current messages
            model: Model being used

        Returns:
            SummaryResult if summarization was performed, None otherwise
        """
        session = await self._session_service.get(session_id)
        if not session:
            return None

        summarizer = self._get_summarizer()

        # Check if we should summarize
        if not await summarizer.should_summarize(session, messages, model):
            return None

        # Perform summarization
        result = await summarizer.summarize(session_id, messages)

        if result:
            # Update session with summary message ID
            session.summary_message_id = result.summary_message.id
            await self._session_service.update(session)

        return result

    async def force_summarize(
        self,
        session_id: str,
        messages: list[Message],
        keep_recent: int = 4,
        extra_user_instructions: str = "",
    ) -> SummaryResult | None:
        """Force summarization of the conversation.

        Args:
            session_id: Session ID
            messages: QAOA turns to summarize
            keep_recent: Number of recent messages to keep

        Returns:
            SummaryResult if successful, None otherwise
        """
        summarizer = self._get_summarizer()
        result = await summarizer.summarize(
            session_id,
            messages,
            keep_recent,
            extra_user_instructions=extra_user_instructions,
        )

        if result:
            # Update session with summary message ID
            session = await self._session_service.get(session_id)
            if session:
                session.summary_message_id = result.summary_message.id
                await self._session_service.update(session)

        return result

    async def get_context_messages(
        self,
        session_id: str,
        max_tokens: int,
    ) -> list[Message]:
        """Get messages for context, using summary if available.

        Args:
            session_id: Session ID
            max_tokens: Maximum tokens for context

        Returns:
            List of messages for context
        """
        messages = await self._message_service.list_by_session(session_id)

        session = await self._session_service.get(session_id)
        if not session:
            return messages

        summarizer = self._get_summarizer()
        return await summarizer.get_context_with_summary(
            session_id,
            messages,
            max_tokens,
        )


__all__ = [
    "Summarizer",
    "SummarizerService",
    "SummarizerConfig",
    "SummaryResult",
    "DEFAULT_MAX_CONTEXT_RATIO",
    "DEFAULT_MIN_MESSAGES_TO_SUMMARIZE",
    "DEFAULT_SUMMARY_PREFIX",
]
