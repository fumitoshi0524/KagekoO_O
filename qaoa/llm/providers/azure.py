"""Azure OpenAI provider for Kageko.

This module provides integration with Azure OpenAI Service.
"""

# QAOA turn: maps to QAOAAction

from __future__ import annotations

from typing import Any, AsyncIterator

from ..base import (
    BaseProvider,
    ProviderEvent,
    ProviderResponse,
    ToolCall,
    TokenUsage,
)


class AzureProvider(BaseProvider):
    """Azure OpenAI provider.

    Supports GPT-4, GPT-4o, and other models deployed on Azure.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        endpoint: str | None = None,
        api_version: str = "2024-02-15-preview",
        deployment_name: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        """Initialize the Azure OpenAI provider.

        Args:
            model: Model/deployment name to use
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            api_version: API version to use
            deployment_name: Azure deployment name (defaults to model)
            max_tokens: Maximum tokens in response
        """
        self._model = model
        self._api_key = api_key
        self._endpoint = endpoint
        self._api_version = api_version
        self._deployment_name = deployment_name or model
        self._max_tokens = max_tokens
        self._client: Any = None

    @property
    def model(self) -> str:
        """Get the model name."""
        return self._model

    async def _get_client(self) -> Any:
        """Get or create the Azure OpenAI client.

        Returns:
            AsyncOpenAI client configured for Azure
        """
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                if not self._api_key:
                    raise ValueError(
                        "Azure OpenAI API key is required. "
                        "Set AZURE_OPENAI_API_KEY environment variable."
                    )
                if not self._endpoint:
                    raise ValueError(
                        "Azure OpenAI endpoint is required. "
                        "Set AZURE_OPENAI_ENDPOINT environment variable."
                    )

                self._client = AsyncOpenAI(
                    api_key=self._api_key,
                    base_url=f"{self._endpoint}/openai/deployments/{self._deployment_name}",
                    default_query={"api-version": self._api_version},
                )
            except ImportError:
                raise ImportError(
                    "openai package is required for Azure provider. "
                    "Install it with: pip install openai"
                )
        return self._client

    def supports_tools(self) -> bool:
        """Check if the current model supports function calling.

        Returns:
            True for most GPT models
        """
        return True  # Azure OpenAI deployments generally support function calling

    async def send_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Send messages to Azure OpenAI and get a response.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool schemas

        Returns:
            Provider response with content and optional tool calls
        """
        client = await self._get_client()

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self._deployment_name,
            "messages": messages,
            "max_tokens": self._max_tokens,
        }

        # Add tools if provided
        if tools:
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
        """Stream response from Azure OpenAI.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool schemas

        Yields:
            Provider events for the stream
        """
        client = await self._get_client()

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self._deployment_name,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "stream": True,
        }

        # Add tools if provided
        if tools:
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


def create_azure_provider(
    model: str = "gpt-4o",
    api_key: str | None = None,
    endpoint: str | None = None,
    **kwargs,
) -> AzureProvider:
    """Create an Azure OpenAI provider instance.

    Args:
        model: Model/deployment name to use
        api_key: Azure OpenAI API key
        endpoint: Azure OpenAI endpoint URL
        **kwargs: Additional arguments

    Returns:
        AzureProvider instance
    """
    return AzureProvider(
        model=model,
        api_key=api_key,
        endpoint=endpoint,
        **kwargs,
    )


__all__ = ["AzureProvider", "create_azure_provider"]
