"""GitHub Copilot LLM provider implementation.

This module provides the GitHub Copilot provider implementation
using the OpenAI-compatible API with GitHub Copilot authentication.
"""

# QAOA turn: maps to QAOAAction

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI

from ..base import (
    BaseProvider,
    ProviderError,
    ProviderEvent,
    ProviderResponse,
    TokenUsage,
    ToolCall,
)


# Supported Copilot models and their API model names
COPILOT_MODELS = {
    "gpt-4o": "gpt-4o",
    "gpt-4.1": "gpt-4.1",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4": "gpt-4",
    "gpt-3.5-turbo": "gpt-3.5-turbo",
    "claude-3.5-sonnet": "claude-3.5-sonnet",
    "claude-3.7-sonnet": "claude-3.7-sonnet",
    "claude-3.7-sonnet-thought": "claude-3.7-sonnet-thought",
    "claude-sonnet-4": "claude-sonnet-4",
    "o1": "o1",
    "o3-mini": "o3-mini",
    "o4-mini": "o4-mini",
    "gemini-2.0-flash": "gemini-2.0-flash-001",
    "gemini-2.5-pro": "gemini-2.5-pro",
}

# Models that support reasoning (use max_completion_tokens instead of max_tokens)
REASONING_MODELS = {
    "o1",
    "o3-mini",
    "o4-mini",
    "gpt-4.1",
    "claude-3.7-sonnet-thought",
}

# Anthropic models that need special handling for tool calls
ANTHROPIC_MODELS = {
    "claude-3.5-sonnet",
    "claude-3.7-sonnet",
    "claude-3.7-sonnet-thought",
    "claude-sonnet-4",
}

# GitHub Copilot API endpoints
COPILOT_API_BASE = "https://api.githubcopilot.com"
GITHUB_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"


class CopilotTokenResponse:
    """Response from GitHub's token exchange endpoint."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.token = data.get("token", "")
        self.expires_at = data.get("expires_at", 0)


class CopilotProvider(BaseProvider):
    """GitHub Copilot LLM provider.

    Supports:
    - GPT-4o, GPT-4.1, GPT-4o-mini
    - Claude 3.5 Sonnet, Claude 3.7 Sonnet, Claude Sonnet 4
    - o1, o3-mini, o4-mini
    - Gemini 2.0 Flash, Gemini 2.5 Pro
    - Tool calling
    - Streaming responses
    """

    # Models that support function calling
    FUNCTION_CALLING_MODELS = {
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-3.5-turbo",
        "claude-3.5-sonnet",
        "claude-3.7-sonnet",
        "claude-sonnet-4",
    }

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 4096,
        system_message: str = "",
        reasoning_effort: str = "medium",
        **kwargs: Any,
    ) -> None:
        """Initialize the Copilot provider.

        Args:
            model: Model identifier (e.g., gpt-4o, claude-3.5-sonnet)
            api_key: GitHub token (defaults to GITHUB_TOKEN env var or .copilotrc)
            base_url: Custom base URL (defaults to GitHub Copilot API)
            max_tokens: Maximum tokens for generation
            system_message: System message to prepend
            reasoning_effort: Reasoning effort level (low, medium, high) for reasoning models
            **kwargs: Additional options
        """
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url or COPILOT_API_BASE,
            max_tokens=max_tokens,
            system_message=system_message,
            **kwargs,
        )

        self._reasoning_effort = reasoning_effort
        self._bearer_token: str | None = None
        self._client: AsyncOpenAI | None = None
        self._http_client: httpx.AsyncClient | None = None

        # Get the API model name
        self._api_model = COPILOT_MODELS.get(model, model)

    @property
    def is_reasoning_model(self) -> bool:
        """Check if the model supports reasoning."""
        return self._api_model in REASONING_MODELS

    @property
    def is_anthropic_model(self) -> bool:
        """Check if the model is an Anthropic model."""
        return self._api_model in ANTHROPIC_MODELS

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def _load_github_token_from_rc(self) -> str | None:
        """Load GitHub token from .copilotrc file.

        Returns:
            Token string or None
        """
        # Check common locations for .copilotrc
        locations = [
            Path.home() / ".copilotrc",
            Path.cwd() / ".copilotrc",
            Path.home() / ".config" / "copilot" / ".copilotrc",
        ]

        for location in locations:
            if location.exists():
                try:
                    content = location.read_text().strip()
                    # Handle simple token file or JSON format
                    if content.startswith("{"):
                        data = json.loads(content)
                        return data.get("token") or data.get("github_token")
                    return content
                except (json.JSONDecodeError, IOError):
                    continue

        return None

    def _load_github_token_from_hosts(self) -> str | None:
        """Load GitHub token from GitHub CLI/hosts configuration.

        Returns:
            OAuth token or None
        """
        # Check GitHub CLI hosts.yml
        hosts_path = Path.home() / ".config" / "gh" / "hosts.yml"
        if hosts_path.exists():
            try:
                import yaml
                with open(hosts_path) as f:
                    hosts = yaml.safe_load(f)
                if hosts and "github.com" in hosts:
                    return hosts["github.com"].get("oauth_token")
            except (ImportError, yaml.YAMLError, IOError):
                pass

        # Check GitHub Copilot hosts.json
        copilot_hosts = Path.home() / ".config" / "github-copilot" / "hosts.json"
        if copilot_hosts.exists():
            try:
                with open(copilot_hosts) as f:
                    hosts = json.load(f)
                if hosts and "github.com" in hosts:
                    return hosts["github.com"].get("oauth_token")
            except (json.JSONDecodeError, IOError):
                pass

        return None

    def _get_github_token(self) -> str | None:
        """Get GitHub token from multiple sources.

        Priority:
        1. api_key parameter
        2. GITHUB_TOKEN environment variable
        3. .copilotrc file
        4. GitHub CLI/hosts configuration

        Returns:
            GitHub token or None
        """
        # 1. API key parameter
        if self.api_key:
            return self.api_key

        # 2. Environment variable
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            return token

        # 3. .copilotrc file
        token = self._load_github_token_from_rc()
        if token:
            return token

        # 4. GitHub CLI/hosts configuration
        token = self._load_github_token_from_hosts()
        if token:
            return token

        return None

    async def _exchange_github_token(self, github_token: str) -> str:
        """Exchange GitHub token for Copilot bearer token.

        Args:
            github_token: GitHub OAuth token

        Returns:
            Copilot bearer token

        Raises:
            ProviderError: If token exchange fails
        """
        client = await self._get_http_client()

        headers = {
            "Authorization": f"Token {github_token}",
            "User-Agent": "Kageko/1.0",
            "Accept": "application/json",
        }

        try:
            response = await client.get(GITHUB_TOKEN_URL, headers=headers)

            if response.status_code != 200:
                raise ProviderError(
                    f"Token exchange failed with status {response.status_code}: {response.text}",
                    provider="copilot",
                    model=self.model,
                )

            data = response.json()
            token_response = CopilotTokenResponse(data)

            if not token_response.token:
                raise ProviderError(
                    "No token in response from GitHub",
                    provider="copilot",
                    model=self.model,
                )

            return token_response.token

        except httpx.HTTPError as e:
            raise ProviderError(
                f"Failed to exchange GitHub token: {e}",
                provider="copilot",
                model=self.model,
                original=e,
            )

    async def _get_bearer_token(self) -> str:
        """Get or refresh the Copilot bearer token.

        Returns:
            Copilot bearer token

        Raises:
            ProviderError: If authentication fails
        """
        if self._bearer_token:
            return self._bearer_token

        github_token = self._get_github_token()
        if not github_token:
            raise ProviderError(
                "GitHub token is required for Copilot provider. "
                "Set GITHUB_TOKEN environment variable, create .copilotrc file, "
                "or ensure GitHub CLI/Copilot is properly authenticated.",
                provider="copilot",
                model=self.model,
            )

        self._bearer_token = await self._exchange_github_token(github_token)
        return self._bearer_token

    async def _get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client configured for Copilot.

        Returns:
            Configured AsyncOpenAI client
        """
        if self._client is not None:
            return self._client

        bearer_token = await self._get_bearer_token()

        # Create OpenAI client with Copilot configuration
        self._client = AsyncOpenAI(
            api_key=bearer_token,
            base_url=self.base_url,
            default_headers={
                "Editor-Version": "Kageko/1.0",
                "Editor-Plugin-Version": "Kageko/1.0",
                "Copilot-Integration-Id": "vscode-chat",
            },
        )

        return self._client

    async def _refresh_client_on_error(self) -> AsyncOpenAI:
        """Refresh the client when token expires.

        Returns:
            New AsyncOpenAI client
        """
        self._bearer_token = None
        self._client = None
        return await self._get_client()

    @property
    def model_identifier(self) -> str:
        """Get the model identifier (user-facing model name)."""
        return self.model

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
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                client = await self._get_client()

                # Prepare request parameters
                request_params = self._prepare_request_params(messages, tools, stream=False)

                # Make request
                response = await client.chat.completions.create(**request_params)

                # Parse response
                return self._parse_response(response)

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check for authentication error - try to refresh token
                if "401" in error_str or "unauthorized" in error_str:
                    try:
                        await self._refresh_client_on_error()
                        continue
                    except Exception:
                        pass

                # Check for rate limit
                if "429" in error_str or "rate" in error_str:
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue

                raise ProviderError(
                    f"Copilot API error: {e}",
                    provider="copilot",
                    model=self.model,
                    original=e,
                )

        raise ProviderError(
            f"Max retries exceeded: {last_error}",
            provider="copilot",
            model=self.model,
            original=last_error,
        )

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
        max_retries = 3

        for attempt in range(max_retries):
            try:
                client = await self._get_client()

                # Prepare request parameters
                request_params = self._prepare_request_params(messages, tools, stream=True)

                # Stream response
                stream = await client.chat.completions.create(**request_params)

                content_buffer = []
                # QAOA Observation point
                tool_calls_buffer: dict[str, dict] = {}
                current_tool_call_id: str | None = None

                async for chunk in stream:
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta

                    # Content delta
                    if delta.content:
                        content = delta.content
                        content_buffer.append(content)
                        yield ProviderEvent.content_delta(content)

                    # Tool call handling
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.index is not None:
                                tool_id = tc.id or f"call_{tc.index}"

                                if tool_id not in tool_calls_buffer:
                                    tool_calls_buffer[tool_id] = {
                                        "id": tool_id,
                                        "name": "",
                                        "arguments": "",
                                    }

                                    if tc.id:
                                        yield ProviderEvent.tool_use_start(
                                            ToolCall(id=tool_id, name="", input={})
                                        )

                                if tc.function:
                                    if tc.function.name:
                                        tool_calls_buffer[tool_id]["name"] = tc.function.name

                                    if tc.function.arguments:
                                        tool_calls_buffer[tool_id]["arguments"] += tc.function.arguments

                # Convert tool calls
                tool_calls = []
                for tc_data in tool_calls_buffer.values():
                    if tc_data["name"]:
                        try:
                            args = self._parse_arguments(tc_data["arguments"])
                        except Exception:
                            args = {}

                        tool_calls.append(
                            ToolCall(
                                id=tc_data["id"],
                                name=tc_data["name"],
                                input=args,
                            )
                        )

                        yield ProviderEvent.tool_use_stop()

                # Get usage from stream if available
                usage = TokenUsage(
                    input_tokens=0,
                    output_tokens=0,
                )

                # Complete event
                content = "".join(content_buffer)
                yield ProviderEvent.complete(
                    ProviderResponse(
                        content=content,
                        tool_calls=tool_calls,
                        usage=usage,
                        finish_reason="stop",
                        model=self.model,
                    )
                )

                return  # Successfully completed

            except Exception as e:
                error_str = str(e).lower()

                # Check for authentication error - try to refresh token
                if "401" in error_str or "unauthorized" in error_str:
                    try:
                        await self._refresh_client_on_error()
                        continue
                    except Exception:
                        pass

                # Check for rate limit
                if "429" in error_str or "rate" in error_str:
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue

                yield ProviderEvent.error(
                    ProviderError(
                        f"Copilot API error: {e}",
                        provider="copilot",
                        model=self.model,
                        original=e,
                    )
                )
                return

        yield ProviderEvent.error(
            ProviderError(
                "Max retries exceeded for streaming",
                provider="copilot",
                model=self.model,
            )
        )

    def _prepare_request_params(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Prepare request parameters for the API call.

        Args:
            messages: Message history
            tools: Available tools
            stream: Whether to stream the response

        Returns:
            Request parameters dictionary
        """
        # Add system message if provided
        formatted_messages = []
        if self.system_message:
            formatted_messages.append({"role": "system", "content": self.system_message})
        formatted_messages.extend(messages)

        params: dict[str, Any] = {
            "model": self._api_model,
            "messages": formatted_messages,
        }

        # Handle max tokens based on model type
        if self.is_reasoning_model:
            params["max_completion_tokens"] = self.max_tokens
            # Add reasoning effort for reasoning models
            if self._reasoning_effort in ("low", "medium", "high"):
                params["reasoning_effort"] = self._reasoning_effort
        else:
            params["max_tokens"] = self.max_tokens

        # Add tools if available and model supports it
        if tools and self._api_model in self.FUNCTION_CALLING_MODELS:
            params["tools"] = self._convert_tools(tools)
            params["tool_choice"] = "auto"

        # Add stream option
        if stream:
            params["stream"] = True
            params["stream_options"] = {"include_usage": True}

        return params

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert tool schemas to OpenAI format.

        Args:
            tools: Tool schemas in standard format

        Returns:
            OpenAI format tools
        """
        openai_tools = []

        for tool in tools:
            # Handle both OpenAI and Anthropic tool formats
            if "function" in tool:
                # Already in OpenAI format
                openai_tools.append(tool)
            else:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {}),
                    },
                }
                openai_tools.append(openai_tool)

        return openai_tools

    def _parse_response(self, response: Any) -> ProviderResponse:
        """Parse the API response.

        Args:
            response: Raw API response

        Returns:
            Provider response
        """
        message = response.choices[0].message
        content = message.content or ""

        # Extract tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        input=self._parse_arguments(tc.function.arguments),
                    )
                )

        # Get usage
        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )

        # Determine finish reason
        finish_reason = response.choices[0].finish_reason or "stop"
        if tool_calls:
            finish_reason = "tool_calls"

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=finish_reason,
            model=self.model,
        )

    def _parse_arguments(self, arguments: str) -> dict | str:
        """Parse function call arguments.

        Args:
            arguments: Arguments JSON string

        Returns:
            Parsed arguments dict or original string if parsing fails
        """
        try:
            return json.loads(arguments)
        except (json.JSONDecodeError, TypeError):
            return arguments

    @property
    def supports_tools(self) -> bool:
        """Check if provider supports tool calling.

        Returns:
            True if tools are supported for this model
        """
        return self._api_model in self.FUNCTION_CALLING_MODELS

    @property
    def supports_attachments(self) -> bool:
        """Check if provider supports file attachments.

        Returns:
            True if attachments are supported for this model
        """
        # Most Copilot models support attachments except o1
        return self._api_model not in {"o1"}

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def create_copilot_provider(
    model: str,
    api_key: str | None = None,
    **kwargs: Any,
) -> CopilotProvider:
    """Factory function to create a Copilot provider.

    Args:
        model: Model identifier (e.g., gpt-4o, claude-3.5-sonnet)
        api_key: GitHub token
        **kwargs: Additional provider options

    Returns:
        CopilotProvider instance
    """
    return CopilotProvider(
        model=model,
        api_key=api_key,
        **kwargs,
    )
