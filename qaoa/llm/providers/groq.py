"""Groq provider for Kageko.

This module provides integration with Groq's API for fast inference.
"""

# QAOA turn: maps to QAOAAction

from __future__ import annotations

from typing import Any, AsyncIterator

from ..base import (
    BaseProvider,
    ProviderEvent,
    ProviderEventType,
    ProviderResponse,
    ToolCall,
    TokenUsage,
)


class GroqProvider(BaseProvider):
    """Groq provider for fast LLM inference.

    Supports Llama, Mixtral, and other models with Groq's fast inference.
    """

    # Models that support function calling
    FUNCTION_CALLING_MODELS = {
        "llama-3.3-70b-versatile",
        "llama-3.3-70b-specdec",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-realtime-preview",
        "llama-3.1-70b",
        "llama-3.1-8b",
        "llama3-groq-70b-8192-tool-use-preview",
        "llama3-groq-8b-8192-tool-use-preview",
        "mixtral-8x7b-32768",
        "qwen-qwq-32b-preview",
        "deepseek-r1-distill-llama-70b",
    }

    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        api_key: str | None = None,
        max_tokens: int = 4096,
        base_url: str = "https://api.groq.com/openai/v1",
    ) -> None:
        """Initialize the Groq provider.

        Args:
            model: Model ID to use
            api_key: Groq API key
            max_tokens: Maximum tokens in response
            base_url: API base URL
        """
        self._model = model
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._base_url = base_url
        self._client: Any = None

    @property
    def model(self) -> str:
        """Get the model name."""
        return self._model

    async def _get_client(self) -> Any:
        """Get or create the Groq client.

        Returns:
            AsyncOpenAI client configured for Groq
        """
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                )
            except ImportError:
                raise ImportError(
                    "openai package is required for Groq provider. "
                    "Install it with: pip install openai"
                )
        return self._client

    def supports_tools(self) -> bool:
        """Check if the current model supports function calling.

        Returns:
            True if the model supports function calling
        """
        return self._model in self.FUNCTION_CALLING_MODELS

    async def send_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Send messages to Groq and get a response.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool schemas

        Returns:
            Provider response with content and optional tool calls
        """
        client = await self._get_client()

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
        }

        # Add tools if supported and provided
        if tools and self.supports_tools():
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Make the API call
        response = await client.chat.completions.create(**kwargs)

        # Extract content
        content = ""
        if response.choices and response.choices[0].message.content:
            content = response.choices[0].message.content

        # QAOA Observation point
        # Extract tool calls
        tool_calls = []
        if response.choices and response.choices[0].message.tool_calls:
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        input=tc.function.arguments
                        if isinstance(tc.function.arguments, dict)
                        else tc.function.arguments,
                    )
                )

        # Extract token usage
        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model,
        )

    async def stream_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream response from Groq.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool schemas

        Yields:
            Provider events for the stream
        """
        client = await self._get_client()

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "stream": True,
        }

        # Add tools if supported and provided
        if tools and self.supports_tools():
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Stream the response
        stream = await client.chat.completions.create(**kwargs)

        tool_calls_buffer: dict[int, dict[str, Any]] = {}
        input_tokens = 0
        output_tokens = 0

        async for chunk in stream:
            # Handle usage info
            if hasattr(chunk, "usage") and chunk.usage:
                input_tokens = chunk.usage.prompt_tokens or 0
                output_tokens = chunk.usage.completion_tokens or 0

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Handle content delta
            if delta.content:
                yield ProviderEvent.content_delta(delta.content)

            # Handle tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index

                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": tc.id or "",
                            "name": "",
                            "arguments": "",
                        }

                    if tc.function:
                        if tc.function.name:
                            tool_calls_buffer[idx]["name"] = tc.function.name
                            yield ProviderEvent.tool_use_start(
                                tc.id or f"call_{idx}",
                                tc.function.name,
                            )
                        if tc.function.arguments:
                            tool_calls_buffer[idx]["arguments"] += tc.function.arguments
                            yield ProviderEvent.tool_use_delta(
                                tc.id or f"call_{idx}",
                                tc.function.arguments,
                            )

        # Yield complete event with final response
        final_tool_calls = []
        for idx in sorted(tool_calls_buffer.keys()):
            tc_data = tool_calls_buffer[idx]
            final_tool_calls.append(
                ToolCall(
                    id=tc_data["id"],
                    name=tc_data["name"],
                    input=tc_data["arguments"],
                )
            )

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        yield ProviderEvent.complete(
            ProviderResponse(
                content="",
                tool_calls=final_tool_calls,
                usage=usage,
                model=self._model,
            )
        )


def create_groq_provider(
    model: str = "llama-3.3-70b-versatile",
    api_key: str | None = None,
    **kwargs,
) -> GroqProvider:
    """Create a Groq provider instance.

    Args:
        model: Model ID to use
        api_key: Groq API key
        **kwargs: Additional arguments

    Returns:
        GroqProvider instance
    """
    return GroqProvider(model=model, api_key=api_key, **kwargs)


__all__ = ["GroqProvider", "create_groq_provider"]
