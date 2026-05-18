"""Google Gemini provider for Kageko.

This module provides integration with Google's Gemini models.
"""

# QAOA turn: maps to QAOAAction

from __future__ import annotations

import os
from typing import Any, AsyncIterator

import google.generativeai as genai

from ..base import (
    BaseProvider,
    ProviderEvent,
    ProviderEventType,
    ProviderResponse,
    ToolCall,
    TokenUsage,
)


class GeminiProvider(BaseProvider):
    """Google Gemini provider.

    Supports Gemini Pro, Gemini Pro Vision, and Gemini Ultra models.
    """

    # Models that support function calling
    FUNCTION_CALLING_MODELS = {
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-thinking-exp",
        "gemini-2.5-pro-preview-03-25",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    }

    def __init__(
        self,
        model: str = "gemini-1.5-pro",
        api_key: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        """Initialize the Gemini provider.

        Args:
            model: Model identifier
            api_key: Google API key (defaults to GEMINI_API_KEY env var)
            max_tokens: Maximum tokens in response
        """
        self._model = model
        self._max_tokens = max_tokens

        # Get API key from parameter or environment
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable.")

        # Configure the generative AI client
        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(model)

    @property
    def model(self) -> str:
        """Get the model identifier.

        Returns:
            Model name
        """
        return self._model

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
        """Send messages and get complete response.

        Args:
            messages: Message history
            tools: Available tools for function calling

        Returns:
            Provider response
        """
        # Convert messages to Gemini format
        contents = self._convert_messages(messages)

        # Prepare generation config
        config = genai.GenerationConfig(
            max_output_tokens=self._max_tokens,
        )

        # Prepare tools if available
        gemini_tools = None
        if tools and self.supports_tools():
            gemini_tools = self._convert_tools(tools)

        # Generate content
        response = await self._client.generate_content_async(
            contents,
            generation_config=config,
            tools=gemini_tools,
        )

        # Parse response
        return self._parse_response(response)

    async def stream_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream response with events.

        Args:
            messages: Message history
            tools: Available tools

        Yields:
            ProviderEvent objects
        """
        # Convert messages to Gemini format
        contents = self._convert_messages(messages)

        # Prepare generation config
        config = genai.GenerationConfig(
            max_output_tokens=self._max_tokens,
        )

        # Prepare tools if available
        gemini_tools = None
        if tools and self.supports_tools():
            gemini_tools = self._convert_tools(tools)

        # Stream content
        response = await self._client.generate_content_async(
            contents,
            generation_config=config,
            tools=gemini_tools,
            stream=True,
        )

        async for chunk in response:
            # Handle text content
            if chunk.text:
                yield ProviderEvent.content_delta(chunk.text)

            # Handle function calls
            if chunk.parts:
                for i, part in enumerate(chunk.parts):
                    if hasattr(part, 'function_call') and part.function_call:
                        yield ProviderEvent.tool_use_start(
                            f"call_{i}",
                            part.function_call.name,
                        )

        # Get final response for usage info
        final_response = await self._client.generate_content_async(
            contents,
            generation_config=config,
            tools=gemini_tools,
        )

        usage = TokenUsage(
            input_tokens=final_response.usage_metadata.prompt_token_count if final_response.usage_metadata else 0,
            output_tokens=final_response.usage_metadata.candidates_token_count if final_response.usage_metadata else 0,
        )

        yield ProviderEvent.complete(
            ProviderResponse(
                content="",
                tool_calls=[],
                usage=usage,
                model=self._model,
            )
        )

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert messages to Gemini format.

        Args:
            messages: Message history in standard format

        Returns:
            Gemini format content list
        """
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles
            gemini_role = "user" if role == "user" else "model"

            # Handle string content
            if isinstance(content, str):
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}],
                })
            # Handle list content (multimodal)
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "")

                        if block_type == "text":
                            parts.append({"text": block.get("content", "")})

                        elif block_type == "image":
                            # Handle image attachments
                            import base64
                            source_type = block.get("source_type", "base64")
                            media_type = block.get("media_type", "image/png")
                            data = block.get("data", "")

                            if source_type == "base64" and data:
                                try:
                                    image_data = base64.b64decode(data)
                                    parts.append({
                                        "inline_data": {
                                            "mime_type": media_type,
                                            "data": image_data,
                                        }
                                    })
                                except Exception:
                                    pass

                        elif block_type == "tool_result":
                            tool_id = block.get("tool_use_id", "")
                            result_content = block.get("content", "")
                            parts.append({"text": f"Tool Result [{tool_id}]: {result_content}"})

                        else:
                            parts.append({"text": str(block)})

                if parts:
                    contents.append({"role": gemini_role, "parts": parts})

        return contents

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list:
        """Convert tool schemas to Gemini format.

        Args:
            tools: Tool schemas in standard format

        Returns:
            Gemini format function declarations
        """
        function_declarations = []

        for tool in tools:
            params = tool.get("parameters", {})
            # Convert parameters schema
            schema = None
            if params:
                schema = genai.Schema(
                    type=params.get("type", "object"),
                    properties=params.get("properties"),
                    required=params.get("required"),
                )

            function_declarations.append(
                genai.FunctionDeclaration(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    parameters=schema,
                )
            )

        return [genai.Tool(function_declarations=function_declarations)]

    def _parse_response(self, response) -> ProviderResponse:
        """Parse a Gemini response.

        Args:
            response: Gemini response

        Returns:
            Provider response
        """
        # Get content
        content = ""
        if response.candidates and response.candidates[0].content:
            parts = response.candidates[0].content.parts
            content = "".join(p.text for p in parts if hasattr(p, 'text') and p.text)

        # QAOA Observation point
        # Extract tool calls
        tool_calls: list[ToolCall] = []
        if response.candidates and response.candidates[0].content:
            parts = response.candidates[0].content.parts
            for i, part in enumerate(parts):
                if hasattr(part, 'function_call') and part.function_call:
                    args = {}
                    if hasattr(part.function_call, 'args') and part.function_call.args:
                        args = dict(part.function_call.args)
                    tool_call = ToolCall(
                        id=f"call_{i}",
                        name=part.function_call.name,
                        input=args,
                    )
                    tool_calls.append(tool_call)

        # Get usage
        usage = TokenUsage(
            input_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            output_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
        )

        finish_reason = "stop"
        if response.candidates:
            fr = response.candidates[0].finish_reason
            if hasattr(fr, 'name'):
                finish_reason = fr.name
            elif hasattr(fr, 'value'):
                finish_reason = str(fr.value)
            else:
                finish_reason = str(fr)

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=finish_reason,
            model=self._model,
        )


def create_gemini_provider(
    model: str = "gemini-1.5-pro",
    api_key: str | None = None,
    max_tokens: int = 4096,
) -> GeminiProvider:
    """Create a Gemini provider instance.

    Args:
        model: Model identifier
        api_key: Google API key
        max_tokens: Maximum tokens

    Returns:
        GeminiProvider instance
    """
    return GeminiProvider(
        model=model,
        api_key=api_key,
        max_tokens=max_tokens,
    )


__all__ = ["GeminiProvider", "create_gemini_provider"]
