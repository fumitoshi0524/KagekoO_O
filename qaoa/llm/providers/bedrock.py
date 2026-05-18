"""AWS Bedrock LLM provider implementation.

This module provides the AWS Bedrock provider implementation for accessing
various foundation models through AWS Bedrock service.
"""

# QAOA turn: maps to QAOAAction

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from ..base import (
    BaseProvider,
    ProviderError,
    ProviderEvent,
    ProviderResponse,
    RateLimitError,
    TokenUsage,
    ToolCall,
)


class BedrockProvider(BaseProvider):
    """AWS Bedrock LLM provider.

    AWS Bedrock provides access to foundation models from various providers
    including Anthropic, AI21, Cohere, Meta, Amazon, and Mistral.

    Supports:
    - Claude models (Anthropic)
    - Titan models (Amazon)
    - Llama models (Meta)
    - Mistral models
    - Tool calling (for supported models)
    - Streaming responses
    """

    # Model provider prefixes
    ANTHROPIC_PREFIX = "anthropic.claude"
    AMAZON_PREFIX = "amazon.titan"
    META_PREFIX = "meta.llama"
    MISTRAL_PREFIX = "mistral"
    COHERE_PREFIX = "cohere"
    AI21_PREFIX = "ai21"

    # Models that support tool calling
    TOOL_SUPPORTING_MODELS = {
        "anthropic.claude-3-5-sonnet",
        "anthropic.claude-3-5-haiku",
        "anthropic.claude-3-sonnet",
        "anthropic.claude-3-haiku",
        "anthropic.claude-3-opus",
        "cohere.command-r",
        "cohere.command-r-plus",
        "mistral.mistral-large",
        "mistral.mistral-small",
    }

    def __init__(
        self,
        model: str,
        api_key: str | None = None,  # Not used for Bedrock, kept for interface compatibility
        base_url: str | None = None,
        max_tokens: int = 4096,
        system_message: str = "",
        region: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        profile_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Bedrock provider.

        Args:
            model: Model identifier (e.g., anthropic.claude-3-5-sonnet-20241022-v2:0)
            api_key: Not used for Bedrock
            base_url: Not used for Bedrock
            max_tokens: Maximum tokens for generation
            system_message: System message
            region: AWS region (defaults to AWS_DEFAULT_REGION or us-east-1)
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_session_token: AWS session token
            profile_name: AWS profile name
            **kwargs: Additional options
        """
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            max_tokens=max_tokens,
            system_message=system_message,
            **kwargs,
        )

        if not HAS_BOTO3:
            raise ImportError(
                "boto3 is required for Bedrock provider. "
                "Install it with: pip install boto3"
            )

        self.region = region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.profile_name = profile_name

        # Bedrock client
        self._client = None
        self._runtime_client = None

    @property
    def client(self):
        """Get or create the Bedrock client.

        Returns:
            The Bedrock client
        """
        if self._client is None:
            session_kwargs = {}
            if self.profile_name:
                session_kwargs["profile_name"] = self.profile_name

            session = boto3.Session(**session_kwargs)

            client_kwargs = {"region_name": self.region}
            if self.aws_access_key_id:
                client_kwargs["aws_access_key_id"] = self.aws_access_key_id
            if self.aws_secret_access_key:
                client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key
            if self.aws_session_token:
                client_kwargs["aws_session_token"] = self.aws_session_token

            self._client = session.client("bedrock", **client_kwargs)
        return self._client

    @property
    def runtime_client(self):
        """Get or create the Bedrock runtime client.

        Returns:
            The Bedrock runtime client
        """
        if self._runtime_client is None:
            session_kwargs = {}
            if self.profile_name:
                session_kwargs["profile_name"] = self.profile_name

            session = boto3.Session(**session_kwargs)

            client_kwargs = {
                "region_name": self.region,
                "config": Config(read_timeout=300, connect_timeout=60),
            }
            if self.aws_access_key_id:
                client_kwargs["aws_access_key_id"] = self.aws_access_key_id
            if self.aws_secret_access_key:
                client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key
            if self.aws_session_token:
                client_kwargs["aws_session_token"] = self.aws_session_token

            self._runtime_client = session.client("bedrock-runtime", **client_kwargs)
        return self._runtime_client

    async def send_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Send messages to Bedrock API.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Returns:
            Complete response
        """
        try:
            # Determine model provider and format accordingly
            if self.model.startswith(self.ANTHROPIC_PREFIX):
                return await self._send_anthropic_messages(messages, tools)
            elif self.model.startswith(self.META_PREFIX):
                return await self._send_llama_messages(messages, tools)
            elif self.model.startswith(self.MISTRAL_PREFIX):
                return await self._send_mistral_messages(messages, tools)
            elif self.model.startswith(self.COHERE_PREFIX):
                return await self._send_cohere_messages(messages, tools)
            else:
                # Default to Anthropic format for unknown models
                return await self._send_anthropic_messages(messages, tools)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ThrottlingException":
                raise RateLimitError(
                    f"Rate limit exceeded: {e}",
                    provider="bedrock",
                    model=self.model,
                    original=e,
                )
            raise ProviderError(
                f"AWS error: {e}",
                provider="bedrock",
                model=self.model,
                original=e,
            )
        except Exception as e:
            raise ProviderError(
                f"Error: {e}",
                provider="bedrock",
                model=self.model,
                original=e,
            )

    async def _send_anthropic_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Send messages using Anthropic/Claude format.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Returns:
            Complete response
        """
        # Prepare the request body
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "messages": self._convert_messages_to_anthropic(messages),
        }

        if self.system_message:
            body["system"] = self.system_message

        if tools:
            body["tools"] = [self._convert_tool_to_anthropic(t) for t in tools]

        response = self.runtime_client.invoke_model(
            modelId=self.model,
            body=json.dumps(body),
        )

        response_body = json.loads(response["body"].read())
        return self._parse_anthropic_response(response_body)

    async def _send_llama_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Send messages using Llama format.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Returns:
            Complete response
        """
        # Llama uses a prompt-based format
        prompt = self._convert_messages_to_llama_prompt(messages)

        body: dict[str, Any] = {
            "prompt": prompt,
            "max_gen_len": self.max_tokens,
        }

        response = self.runtime_client.invoke_model(
            modelId=self.model,
            body=json.dumps(body),
        )

        response_body = json.loads(response["body"].read())
        return self._parse_llama_response(response_body)

    async def _send_mistral_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Send messages using Mistral format.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Returns:
            Complete response
        """
        body: dict[str, Any] = {
            "messages": self._convert_messages_to_openai(messages),
            "max_tokens": self.max_tokens,
        }

        if tools:
            body["tools"] = [self._convert_tool_to_openai(t) for t in tools]

        response = self.runtime_client.invoke_model(
            modelId=self.model,
            body=json.dumps(body),
        )

        response_body = json.loads(response["body"].read())
        return self._parse_mistral_response(response_body)

    async def _send_cohere_messages(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Send messages using Cohere format.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Returns:
            Complete response
        """
        # Cohere uses a different message format
        preamble = self.system_message or None
        chat_history = []
        message = ""

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                if message:  # Already have a message, add to history
                    chat_history.append({"role": "USER", "message": message})
                message = content
            elif role == "assistant":
                chat_history.append({"role": "CHATBOT", "message": content})

        body: dict[str, Any] = {
            "message": message,
            "max_tokens": self.max_tokens,
        }

        if preamble:
            body["preamble"] = preamble
        if chat_history:
            body["chat_history"] = chat_history
        if tools:
            body["tools"] = [self._convert_tool_to_cohere(t) for t in tools]

        response = self.runtime_client.invoke_model(
            modelId=self.model,
            body=json.dumps(body),
        )

        response_body = json.loads(response["body"].read())
        return self._parse_cohere_response(response_body)

    async def stream_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream response from Bedrock API.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Yields:
            ProviderEvent objects
        """
        try:
            # Determine model provider and format accordingly
            if self.model.startswith(self.ANTHROPIC_PREFIX):
                async for event in self._stream_anthropic_response(messages, tools):
                    yield event
            elif self.model.startswith(self.META_PREFIX):
                async for event in self._stream_llama_response(messages, tools):
                    yield event
            elif self.model.startswith(self.MISTRAL_PREFIX):
                async for event in self._stream_mistral_response(messages, tools):
                    yield event
            else:
                async for event in self._stream_anthropic_response(messages, tools):
                    yield event

        except ClientError as e:
            yield ProviderEvent.error(
                ProviderError(
                    f"AWS error: {e}",
                    provider="bedrock",
                    model=self.model,
                    original=e,
                )
            )
        except Exception as e:
            yield ProviderEvent.error(e)

    async def _stream_anthropic_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream Anthropic/Claude response.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Yields:
            ProviderEvent objects
        """
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "messages": self._convert_messages_to_anthropic(messages),
        }

        if self.system_message:
            body["system"] = self.system_message

        if tools:
            body["tools"] = [self._convert_tool_to_anthropic(t) for t in tools]

        response = self.runtime_client.invoke_model_with_response_stream(
            modelId=self.model,
            body=json.dumps(body),
        )

        content = ""
        # QAOA Observation point
        tool_calls: list[ToolCall] = []
        current_tool: ToolCall | None = None
        usage = None

        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            event_type = chunk.get("type", "")

            if event_type == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    content += text
                    yield ProviderEvent.content_delta(text)

            elif event_type == "content_block_start":
                block = chunk.get("content_block", {})
                if block.get("type") == "tool_use":
                    current_tool = ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        input={},
                        finished=False,
                    )
                    tool_calls.append(current_tool)
                    yield ProviderEvent.tool_use_start(current_tool)

            elif event_type == "content_block_stop":
                if current_tool:
                    current_tool.finished = True
                    yield ProviderEvent.tool_use_stop()
                    current_tool = None

            elif event_type == "message_delta":
                if "usage" in chunk:
                    usage = TokenUsage(
                        input_tokens=chunk["usage"].get("input_tokens", 0),
                        output_tokens=chunk["usage"].get("output_tokens", 0),
                    )

            elif event_type == "message_stop":
                response_obj = ProviderResponse(
                    content=content,
                    tool_calls=tool_calls,
                    usage=usage,
                    finish_reason="stop",
                    model=self.model,
                )
                yield ProviderEvent.complete(response_obj)

    async def _stream_llama_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream Llama response.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Yields:
            ProviderEvent objects
        """
        prompt = self._convert_messages_to_llama_prompt(messages)

        body: dict[str, Any] = {
            "prompt": prompt,
            "max_gen_len": self.max_tokens,
        }

        response = self.runtime_client.invoke_model_with_response_stream(
            modelId=self.model,
            body=json.dumps(body),
        )

        content = ""

        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])

            if "generation" in chunk:
                text = chunk["generation"]
                content += text
                yield ProviderEvent.content_delta(text)

            if chunk.get("stop_reason"):
                usage = TokenUsage(
                    input_tokens=chunk.get("prompt_token_count", 0),
                    output_tokens=chunk.get("generation_token_count", 0),
                )
                response_obj = ProviderResponse(
                    content=content,
                    usage=usage,
                    finish_reason=chunk["stop_reason"],
                    model=self.model,
                )
                yield ProviderEvent.complete(response_obj)

    async def _stream_mistral_response(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        """Stream Mistral response.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Yields:
            ProviderEvent objects
        """
        body: dict[str, Any] = {
            "messages": self._convert_messages_to_openai(messages),
            "max_tokens": self.max_tokens,
        }

        if tools:
            body["tools"] = [self._convert_tool_to_openai(t) for t in tools]

        response = self.runtime_client.invoke_model_with_response_stream(
            modelId=self.model,
            body=json.dumps(body),
        )

        content = ""
        tool_calls: list[ToolCall] = []

        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])

            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})

                if "content" in delta and delta["content"]:
                    text = delta["content"]
                    content += text
                    yield ProviderEvent.content_delta(text)

                if "tool_calls" in delta:
                    for tc in delta["tool_calls"]:
                        tool_calls.append(
                            ToolCall(
                                id=tc.get("id", ""),
                                name=tc.get("function", {}).get("name", ""),
                                input=json.loads(tc.get("function", {}).get("arguments", "{}")),
                                finished=True,
                            )
                        )

                if choice.get("finish_reason"):
                    usage = TokenUsage(
                        input_tokens=chunk.get("usage", {}).get("prompt_tokens", 0),
                        output_tokens=chunk.get("usage", {}).get("completion_tokens", 0),
                    )
                    response_obj = ProviderResponse(
                        content=content,
                        tool_calls=tool_calls,
                        usage=usage,
                        finish_reason=choice["finish_reason"],
                        model=self.model,
                    )
                    yield ProviderEvent.complete(response_obj)

    def _convert_messages_to_anthropic(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert messages to Anthropic format.

        Args:
            messages: Original messages

        Returns:
            Anthropic-formatted messages
        """
        formatted = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Anthropic doesn't use system role in messages
            if role == "system":
                continue

            # Handle tool results
            if role == "tool":
                formatted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": content,
                    }],
                })
            # Handle assistant with tool calls
            elif role == "assistant" and "tool_calls" in msg:
                content_blocks = [{"type": "text", "text": content}] if content else []
                for tc in msg["tool_calls"]:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", tc.get("name", "")),
                        "input": tc.get("function", {}).get("arguments", tc.get("input", {})),
                    })
                formatted.append({"role": "assistant", "content": content_blocks})
            else:
                formatted.append({"role": role, "content": content})

        return formatted

    def _convert_messages_to_openai(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert messages to OpenAI format.

        Args:
            messages: Original messages

        Returns:
            OpenAI-formatted messages
        """
        formatted = []

        if self.system_message:
            formatted.append({"role": "system", "content": self.system_message})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                continue

            formatted.append({"role": role, "content": content})

        return formatted

    def _convert_messages_to_llama_prompt(self, messages: list[dict[str, Any]]) -> str:
        """Convert messages to Llama prompt format.

        Args:
            messages: Original messages

        Returns:
            Prompt string
        """
        parts = []

        if self.system_message:
            parts.append(f"<|system|>\n{self.system_message}</s>")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                continue
            elif role == "user":
                parts.append(f"<|user|>\n{content}</s>")
            elif role == "assistant":
                parts.append(f"<|assistant|)\n{content}</s>")

        parts.append("<|assistant|)")
        return "\n".join(parts)

    def _convert_tool_to_anthropic(self, tool: dict[str, Any]) -> dict[str, Any]:
        """Convert tool to Anthropic format.

        Args:
            tool: Tool definition

        Returns:
            Anthropic-formatted tool
        """
        if "function" in tool:
            func = tool["function"]
            return {
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {}),
            }
        return tool

    def _convert_tool_to_openai(self, tool: dict[str, Any]) -> dict[str, Any]:
        """Convert tool to OpenAI format.

        Args:
            tool: Tool definition

        Returns:
            OpenAI-formatted tool
        """
        if "type" in tool and "function" in tool:
            return tool
        elif "function" in tool:
            return {"type": "function", "function": tool["function"]}
        else:
            return {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                },
            }

    def _convert_tool_to_cohere(self, tool: dict[str, Any]) -> dict[str, Any]:
        """Convert tool to Cohere format.

        Args:
            tool: Tool definition

        Returns:
            Cohere-formatted tool
        """
        if "function" in tool:
            func = tool["function"]
            return {
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameter_definitions": func.get("parameters", {}).get("properties", {}),
            }
        return tool

    def _parse_anthropic_response(self, response: dict[str, Any]) -> ProviderResponse:
        """Parse Anthropic response.

        Args:
            response: Raw response dict

        Returns:
            Provider response
        """
        content = ""
        tool_calls = []

        for block in response.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        input=block.get("input", {}),
                        finished=True,
                    )
                )

        usage = None
        if "usage" in response:
            usage = TokenUsage(
                input_tokens=response["usage"].get("input_tokens", 0),
                output_tokens=response["usage"].get("output_tokens", 0),
            )

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=response.get("stop_reason", "stop"),
            model=self.model,
        )

    def _parse_llama_response(self, response: dict[str, Any]) -> ProviderResponse:
        """Parse Llama response.

        Args:
            response: Raw response dict

        Returns:
            Provider response
        """
        content = response.get("generation", "")

        usage = None
        if "prompt_token_count" in response:
            usage = TokenUsage(
                input_tokens=response.get("prompt_token_count", 0),
                output_tokens=response.get("generation_token_count", 0),
            )

        return ProviderResponse(
            content=content,
            usage=usage,
            finish_reason=response.get("stop_reason", "stop"),
            model=self.model,
        )

    def _parse_mistral_response(self, response: dict[str, Any]) -> ProviderResponse:
        """Parse Mistral response.

        Args:
            response: Raw response dict

        Returns:
            Provider response
        """
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})

        content = message.get("content", "") or ""
        tool_calls = []

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
            model=self.model,
        )

    def _parse_cohere_response(self, response: dict[str, Any]) -> ProviderResponse:
        """Parse Cohere response.

        Args:
            response: Raw response dict

        Returns:
            Provider response
        """
        content = response.get("text", "")
        tool_calls = []

        if "tool_calls" in response:
            for tc in response["tool_calls"]:
                tool_calls.append(
                    ToolCall(
                        id=tc.get("name", ""),  # Cohere uses name as ID
                        name=tc.get("name", ""),
                        input=tc.get("parameters", {}),
                        finished=True,
                    )
                )

        usage = None
        if "meta" in response and "tokens" in response["meta"]:
            tokens = response["meta"]["tokens"]
            usage = TokenUsage(
                input_tokens=tokens.get("input_tokens", 0),
                output_tokens=tokens.get("output_tokens", 0),
            )

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason="stop" if response.get("finish_reason") == "COMPLETE" else response.get("finish_reason", "stop"),
            model=self.model,
        )

    @property
    def supports_tools(self) -> bool:
        """Check if provider supports tool calling.

        Returns:
            True if tools are supported
        """
        for prefix in self.TOOL_SUPPORTING_MODELS:
            if self.model.startswith(prefix):
                return True
        return False


def create_bedrock_provider(
    model: str,
    api_key: str | None = None,
    **kwargs: Any,
) -> BedrockProvider:
    """Factory function to create a Bedrock provider.

    Args:
        model: Model identifier (e.g., anthropic.claude-3-5-sonnet-20241022-v2:0)
        api_key: Not used for Bedrock
        **kwargs: Additional provider options (region, aws_access_key_id, etc.)

    Returns:
        BedrockProvider instance
    """
    return BedrockProvider(
        model=model,
        api_key=api_key,
        **kwargs,
    )
