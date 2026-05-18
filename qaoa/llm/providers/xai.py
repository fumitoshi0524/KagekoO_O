"""xAI (Grok) LLM provider implementation.

This module provides the xAI provider implementation for accessing
Grok and other xAI models.
"""

# QAOA turn: maps to QAOAAction

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

import httpx

from ..base import (
    BaseProvider,
    ProviderError,
    ProviderEvent,
    ProviderResponse,
    RateLimitError,
    TokenUsage,
    ToolCall,
)


class XAIProvider(BaseProvider):
    """xAI (Grok) LLM provider.

    xAI provides access to Grok models with tool calling support.

    Supports:
    - Grok-2 and Grok-2-mini models
    - Tool calling
    - Streaming responses
    - Vision capabilities (Grok Vision)
    """

    DEFAULT_BASE_URL = "https://api.x.ai/v1"

    # Available models
    MODELS = {
        "grok-2-1212": {"context_window": 131072, "supports_vision": False},
        "grok-2-vision-1212": {"context_window": 32768, "supports_vision": True},
        "grok-2": {"context_window": 131072, "supports_vision": False},
        "grok-2-mini": {"context_window": 131072, "supports_vision": False},
        "grok-beta": {"context_window": 131072, "supports_vision": False},
        "grok-vision-beta": {"context_window": 8192, "supports_vision": True},
    }

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 4096,
        system_message: str = "",
        **kwargs: Any,
    ) -> None:
        """Initialize the xAI provider.

        Args:
            model: Model identifier (e.g., grok-2, grok-2-vision-1212)
            api_key: xAI API key
            base_url: Custom base URL
            max_tokens: Maximum tokens for generation
            system_message: System message
            **kwargs: Additional options
        """
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
            max_tokens=max_tokens,
            system_message=system_message,
            **kwargs,
        )

        # HTTP client
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            The async HTTP client
        """
        if self._client is None:
            api_key = self.api_key or os.environ.get("XAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "xAI API key is required. "
                    "Set XAI_API_KEY environment variable or pass api_key parameter."
                )

            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=30.0),
            )
        return self._client

    async def send_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Send messages to xAI API.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Returns:
            Complete response
        """
        try:
            # Prepare messages
            formatted_messages = self._prepare_messages(messages)

            # Build request body
            body: dict[str, Any] = {
                "model": self.model,
                "messages": formatted_messages,
                "max_tokens": self.max_tokens,
            }

            # Add tools if provided
            if tools:
                body["tools"] = [self._convert_tool(t) for t in tools]

            # Make the API call
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=body,
            )
            response.raise_for_status()

            # Parse response
            return self._parse_response(response.json())

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError(
                    f"Rate limit exceeded: {e}",
                    provider="xai",
                    model=self.model,
                    original=e,
                )
            raise ProviderError(
                f"API error: {e}",
                provider="xai",
                model=self.model,
                original=e,
            )
        except httpx.RequestError as e:
            raise ProviderError(
                f"Connection error: {e}",
                provider="xai",
                model=self.model,
                original=e,
            )

    async def stream_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream response from xAI API.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Yields:
            ProviderEvent objects
        """
        try:
            # Prepare messages
            formatted_messages = self._prepare_messages(messages)

            # Build request body
            body: dict[str, Any] = {
                "model": self.model,
                "messages": formatted_messages,
                "max_tokens": self.max_tokens,
                "stream": True,
            }

            # Add tools if provided
            if tools:
                body["tools"] = [self._convert_tool(t) for t in tools]

            # Stream the API call
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=body,
            ) as response:
                response.raise_for_status()

                content = ""
                # QAOA Observation point
                tool_calls: list[ToolCall] = []
                current_tool_calls: dict[int, ToolCall] = {}

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data = line[6:]  # Remove "data: " prefix
                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    delta = chunk.get("choices", [{}])[0].get("delta", {})

                    # Handle content
                    if "content" in delta and delta["content"]:
                        text = delta["content"]
                        content += text
                        yield ProviderEvent.content_delta(text)

                    # Handle tool calls
                    if "tool_calls" in delta:
                        for tool_call_delta in delta["tool_calls"]:
                            index = tool_call_delta.get("index", 0)

                            if index not in current_tool_calls:
                                # Start new tool call
                                tool_id = tool_call_delta.get("id", f"tool_{index}")
                                func = tool_call_delta.get("function", {})
                                current_tool_calls[index] = ToolCall(
                                    id=tool_id,
                                    name=func.get("name", ""),
                                    input="",
                                    finished=False,
                                )
                                tool_calls.append(current_tool_calls[index])
                                yield ProviderEvent.tool_use_start(current_tool_calls[index])

                            # Accumulate function arguments
                            func = tool_call_delta.get("function", {})
                            if "arguments" in func:
                                if isinstance(current_tool_calls[index].input, str):
                                    current_tool_calls[index].input += func["arguments"]

                    # Handle finish
                    finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")
                    if finish_reason:
                        # Parse tool call inputs
                        for tool_call in tool_calls:
                            if isinstance(tool_call.input, str):
                                try:
                                    tool_call.input = json.loads(tool_call.input)
                                except json.JSONDecodeError:
                                    tool_call.input = {}
                            tool_call.finished = True
                            yield ProviderEvent.tool_use_stop()

                        # Get usage
                        usage = None
                        if "usage" in chunk:
                            usage = TokenUsage(
                                input_tokens=chunk["usage"].get("prompt_tokens", 0),
                                output_tokens=chunk["usage"].get("completion_tokens", 0),
                            )

                        response_obj = ProviderResponse(
                            content=content,
                            tool_calls=tool_calls,
                            usage=usage,
                            finish_reason=finish_reason or "stop",
                            model=self.model,
                        )
                        yield ProviderEvent.complete(response_obj)

        except httpx.HTTPStatusError as e:
            yield ProviderEvent.error(
                ProviderError(
                    f"API error: {e}",
                    provider="xai",
                    model=self.model,
                    original=e,
                )
            )
        except Exception as e:
            yield ProviderEvent.error(e)

    def _prepare_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prepare messages for xAI API.

        Args:
            messages: Original messages

        Returns:
            Prepared messages
        """
        formatted = []

        # Add system message if present
        if self.system_message:
            formatted.append({"role": "system", "content": self.system_message})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle tool results
            if role == "tool":
                formatted.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": content,
                })
            # Handle assistant with tool calls
            elif role == "assistant" and "tool_calls" in msg:
                formatted.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": msg["tool_calls"],
                })
            # Handle multimodal content
            elif isinstance(content, list):
                formatted.append({"role": role, "content": content})
            else:
                formatted.append({"role": role, "content": content})

        return formatted

    def _convert_tool(self, tool: dict[str, Any]) -> dict[str, Any]:
        """Convert tool to xAI/OpenAI format.

        Args:
            tool: Tool definition

        Returns:
            OpenAI-formatted tool
        """
        if "type" in tool and tool["type"] == "function":
            return tool
        elif "function" in tool:
            return tool
        else:
            return {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                },
            }

    def _parse_response(self, response: dict[str, Any]) -> ProviderResponse:
        """Parse xAI response.

        Args:
            response: Raw response dict

        Returns:
            Provider response
        """
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})

        content = message.get("content", "") or ""
        tool_calls = []

        # Parse tool calls
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                tool_input = func.get("arguments", "{}")
                if isinstance(tool_input, str):
                    try:
                        tool_input = json.loads(tool_input)
                    except json.JSONDecodeError:
                        tool_input = {}

                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", ""),
                        name=func.get("name", ""),
                        input=tool_input,
                        finished=True,
                    )
                )

        usage = None
        if "usage" in response:
            usage = TokenUsage(
                input_tokens=response["usage"].get("prompt_tokens", 0),
                output_tokens=response["usage"].get("completion_tokens", 0),
            )

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=choice.get("finish_reason", "stop"),
            model=response.get("model", self.model),
        )

    @property
    def supports_attachments(self) -> bool:
        """Check if provider supports file attachments.

        Returns:
            True if attachments are supported (vision models)
        """
        model_info = self.MODELS.get(self.model, {})
        return model_info.get("supports_vision", False)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


def create_xai_provider(
    model: str,
    api_key: str | None = None,
    **kwargs: Any,
) -> XAIProvider:
    """Factory function to create an xAI provider.

    Args:
        model: Model identifier (e.g., grok-2, grok-2-vision-1212)
        api_key: API key
        **kwargs: Additional provider options

    Returns:
        XAIProvider instance
    """
    return XAIProvider(
        model=model,
        api_key=api_key,
        **kwargs,
    )
