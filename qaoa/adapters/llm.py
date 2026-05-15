"""LLM adapters with native function/tool calling and streaming support.

All adapters implement:
    complete(*, messages, tools, tool_choice) -> LLMResponse
    complete_stream(*, messages, tools, tool_choice) -> Iterator[StreamEvent]
    complete_text(prompt) -> str  (backward-compatible wrapper)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Protocol, runtime_checkable, Iterator

from ..streaming import StreamEvent, StreamEventType


# ── Provider-agnostic types ───────────────────────────────────────────

@dataclass(slots=True, kw_only=True)
class ToolSchema:
    """Provider-agnostic tool/function schema."""
    name: str
    description: str
    parameters: dict  # JSON Schema for parameters


@dataclass(slots=True, kw_only=True)
class ToolCallResult:
    """A tool call returned by the LLM."""
    id: str
    name: str
    arguments: dict


@dataclass(slots=True, kw_only=True)
class LLMResponse:
    """Structured LLM response with optional tool calls."""
    content: str | None = None
    tool_calls: list[ToolCallResult] = field(default_factory=list)
    stop_reason: str = ""  # "stop", "tool_calls", "length", "error"


# ── Schema conversion ─────────────────────────────────────────────────

def _sanitize_tool_name(name: str) -> str:
    """Replace characters that are invalid in API function names."""
    return name.replace(".", "_")


def _build_schema_name(name: str) -> tuple[str, str]:
    """Return (original_name, api_safe_name) for a tool."""
    return name, _sanitize_tool_name(name)


def tool_spec_to_schema(spec) -> ToolSchema:
    """Convert a ToolSpec (from tools.py) to a ToolSchema."""
    from .tools import ToolSpec
    if isinstance(spec, ToolSpec):
        _, safe_name = _build_schema_name(spec.name)
        return ToolSchema(
            name=safe_name,
            description=spec.description,
            parameters={"type": "object", "properties": {}, "required": []},
        )
    # Fallback for dict-based specs
    name = spec.get("name", "unknown")
    _, safe_name = _build_schema_name(name)
    return ToolSchema(
        name=safe_name,
        description=spec.get("description", ""),
        parameters=spec.get("schema", {"type": "object", "properties": {}, "required": []}),
    )


def build_name_map(schemas: list[ToolSchema], specs: list) -> dict[str, str]:
    """Build a mapping from API-safe names back to original tool names."""
    mapping: dict[str, str] = {}
    for schema in schemas:
        for spec in specs:
            if hasattr(spec, 'name'):
                orig = spec.name
            elif isinstance(spec, dict):
                orig = spec.get('name', '')
            else:
                continue
            safe = _sanitize_tool_name(orig)
            if safe == schema.name:
                mapping[safe] = orig
                break
    return mapping

def to_openai_tools(schemas: list[ToolSchema]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters,
            },
        }
        for s in schemas
    ]


def to_anthropic_tools(schemas: list[ToolSchema]) -> list[dict]:
    return [
        {
            "name": s.name,
            "description": s.description,
            "input_schema": s.parameters,
        }
        for s in schemas
    ]


def to_gemini_tools(schemas: list[ToolSchema]) -> list[dict]:
    declarations = []
    for s in schemas:
        props = s.parameters.get("properties", {})
        declarations.append({
            "name": s.name,
            "description": s.description,
            "parameters": {
                "type": "object",
                "properties": {
                    name: {"type": "string", "description": desc}
                    for name, desc in props.items()
                } if props else {"input": {"type": "string", "description": "Tool input"}},
                "required": list(props.keys()) if props else ["input"],
            },
        })
    return declarations


# ── Adapter protocol ──────────────────────────────────────────────────

@runtime_checkable
class LLMAdapterProtocol(Protocol):
    def complete(self, *, messages: list[dict], tools: list[ToolSchema] | None = None,
                 tool_choice: str | None = None) -> LLMResponse: ...
    def complete_text(self, prompt: str) -> str: ...


# ── OpenAI Chat Completions Adapter ───────────────────────────────────

@dataclass(slots=True, kw_only=True)
class OpenAIAdapter:
    client: object  # OpenAI
    model: str

    def complete(self, *, messages: list[dict], tools: list[ToolSchema] | None = None,
                 tool_choice: str | None = None) -> LLMResponse:
        kwargs: dict = dict(model=self.model, messages=messages)
        if tools:
            kwargs["tools"] = to_openai_tools(tools)
            kwargs["tool_choice"] = tool_choice or "auto"
        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0] if response.choices else None
        if choice is None:
            return LLMResponse(stop_reason="error")

        msg = choice.message
        tool_calls: list[ToolCallResult] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"input": tc.function.arguments}
                tool_calls.append(ToolCallResult(
                    id=tc.id, name=tc.function.name, arguments=args,
                ))

        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            stop_reason="tool_calls" if tool_calls else (choice.finish_reason or "stop"),
        )

    def complete_text(self, prompt: str) -> str:
        response = self.complete(messages=[{"role": "user", "content": prompt}])
        if response.content is None:
            raise RuntimeError("Provider returned an empty response.")
        return response.content

    def complete_stream(self, *, messages: list[dict], tools: list[ToolSchema] | None = None,
                        tool_choice: str | None = None) -> Iterator[StreamEvent]:
        kwargs: dict = dict(model=self.model, messages=messages, stream=True)
        if tools:
            kwargs["tools"] = to_openai_tools(tools)
            kwargs["tool_choice"] = tool_choice or "auto"
        stream = self.client.chat.completions.create(**kwargs)

        tool_call_buffer: dict[int, dict] = {}
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue
            # Text content
            if delta.content:
                yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=delta.content)
            # Tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index or 0
                    if idx not in tool_call_buffer:
                        tool_call_buffer[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_START,
                            tool_id=tc.id, tool_name="",
                        )
                    buf = tool_call_buffer[idx]
                    if tc.id:
                        buf["id"] = tc.id
                    if tc.function and tc.function.name:
                        buf["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        buf["arguments"] += tc.function.arguments
                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_ARGS,
                            tool_id=buf["id"], tool_name=buf["name"],
                            text=tc.function.arguments,
                        )
        # Emit completed tool calls
        for idx, buf in tool_call_buffer.items():
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_END,
                tool_id=buf["id"], tool_name=buf["name"], tool_input=buf["arguments"],
            )
        yield StreamEvent(type=StreamEventType.DONE)


# ── Anthropic Messages Adapter ────────────────────────────────────────

@dataclass(slots=True, kw_only=True)
class AnthropicAdapter:
    client: object  # Anthropic
    model: str
    max_tokens: int = 4096

    def complete(self, *, messages: list[dict], tools: list[ToolSchema] | None = None,
                 tool_choice: str | None = None) -> LLMResponse:
        kwargs: dict = dict(model=self.model, max_tokens=self.max_tokens, messages=messages)
        if tools:
            kwargs["tools"] = to_anthropic_tools(tools)
        response = self.client.messages.create(**kwargs)

        content_text: list[str] = []
        tool_calls: list[ToolCallResult] = []
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                content_text.append(getattr(block, "text", ""))
            elif block_type == "tool_use":
                tool_calls.append(ToolCallResult(
                    id=getattr(block, "id", ""),
                    name=getattr(block, "name", ""),
                    arguments=getattr(block, "input", {}),
                ))

        text = "\n".join(content_text).strip() if content_text else None
        stop = "tool_calls" if tool_calls else getattr(response, "stop_reason", "stop") or "stop"
        return LLMResponse(content=text or None, tool_calls=tool_calls, stop_reason=stop)

    def complete_text(self, prompt: str) -> str:
        response = self.complete(messages=[{"role": "user", "content": prompt}])
        if response.content is None:
            raise RuntimeError("Provider returned an empty Claude response.")
        return response.content

    def complete_stream(self, *, messages: list[dict], tools: list[ToolSchema] | None = None,
                        tool_choice: str | None = None) -> Iterator[StreamEvent]:
        kwargs: dict = dict(model=self.model, max_tokens=self.max_tokens, messages=messages,
                            stream=True)
        if tools:
            kwargs["tools"] = to_anthropic_tools(tools)
        stream = self.client.messages.create(**kwargs)

        current_tool_id: str | None = None
        current_tool_name: str = ""
        current_tool_input: dict = {}
        for event in stream:
            etype = getattr(event, "type", None)
            if etype == "content_block_delta":
                delta = getattr(event, "delta", None)
                if delta is None:
                    continue
                dt = getattr(delta, "type", None)
                if dt == "text_delta":
                    yield StreamEvent(type=StreamEventType.TEXT_DELTA,
                                      text=getattr(delta, "text", ""))
                elif dt == "input_json_delta":
                    partial = getattr(delta, "partial_json", "")
                    if partial:
                        yield StreamEvent(type=StreamEventType.TOOL_CALL_ARGS,
                                          tool_id=current_tool_id or "",
                                          tool_name=current_tool_name, text=partial)
            elif etype == "content_block_start":
                block = getattr(event, "content_block", None)
                if block and getattr(block, "type", None) == "tool_use":
                    current_tool_id = getattr(block, "id", "")
                    current_tool_name = getattr(block, "name", "")
                    current_tool_input = {}
                    yield StreamEvent(type=StreamEventType.TOOL_CALL_START,
                                      tool_id=current_tool_id,
                                      tool_name=current_tool_name)
            elif etype == "content_block_stop":
                if current_tool_id:
                    yield StreamEvent(type=StreamEventType.TOOL_CALL_END,
                                      tool_id=current_tool_id,
                                      tool_name=current_tool_name,
                                      tool_input=json.dumps(current_tool_input))
                    current_tool_id = None
        yield StreamEvent(type=StreamEventType.DONE)


# ── Gemini Adapter ────────────────────────────────────────────────────

@dataclass(slots=True, kw_only=True)
class GeminiAdapter:
    client: object  # genai.Client
    model: str

    def complete(self, *, messages: list[dict], tools: list[ToolSchema] | None = None,
                 tool_choice: str | None = None) -> LLMResponse:
        from google.genai import types as genai_types

        # Convert messages to Gemini contents format
        contents: list[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                contents.append(f"System: {content}")
            elif role == "tool":
                name = msg.get("name", "tool")
                contents.append(f"Tool result ({name}): {content}")
            else:
                prefix = "Assistant" if role == "assistant" else "User"
                contents.append(f"{prefix}: {content}")

        config_kwargs: dict = {}
        if tools:
            config_kwargs["tools"] = to_gemini_tools(tools)

        response = self.client.models.generate_content(
            model=self.model,
            contents="\n".join(contents),
            config=genai_types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
        )

        text = getattr(response, "text", None)
        tool_calls: list[ToolCallResult] = []

        # Parse function calls from Gemini response
        for candidate in getattr(response, "candidates", []) or []:
            for part in getattr(candidate.content, "parts", []) or []:
                fn_call = getattr(part, "function_call", None)
                if fn_call is not None:
                    tool_calls.append(ToolCallResult(
                        id=getattr(fn_call, "id", f"gc-{len(tool_calls)}"),
                        name=getattr(fn_call, "name", ""),
                        arguments=dict(getattr(fn_call, "args", {}) or {}),
                    ))

        if text is None and not tool_calls:
            raise RuntimeError("Provider returned an empty Gemini response.")

        stop = "tool_calls" if tool_calls else "stop"
        return LLMResponse(content=text, tool_calls=tool_calls, stop_reason=stop)

    def complete_text(self, prompt: str) -> str:
        response = self.complete(messages=[{"role": "user", "content": prompt}])
        if response.content is None:
            raise RuntimeError("Provider returned an empty Gemini response.")
        return response.content

    def complete_stream(self, *, messages: list[dict], tools: list[ToolSchema] | None = None,
                        tool_choice: str | None = None) -> Iterator[StreamEvent]:
        from google.genai import types as genai_types

        contents: list[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                contents.append(f"System: {content}")
            elif role == "tool":
                contents.append(f"Tool result ({msg.get('name', 'tool')}): {content}")
            else:
                prefix = "Assistant" if role == "assistant" else "User"
                contents.append(f"{prefix}: {content}")

        config_kwargs: dict = {}
        if tools:
            config_kwargs["tools"] = to_gemini_tools(tools)

        response = self.client.models.generate_content_stream(
            model=self.model,
            contents="\n".join(contents),
            config=genai_types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
        )

        for chunk in response:
            text = getattr(chunk, "text", None)
            if text:
                yield StreamEvent(type=StreamEventType.TEXT_DELTA, text=text)
            for candidate in getattr(chunk, "candidates", []) or []:
                for part in getattr(candidate.content, "parts", []) or []:
                    fn_call = getattr(part, "function_call", None)
                    if fn_call is not None:
                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_END,
                            tool_id=getattr(fn_call, "id", ""),
                            tool_name=getattr(fn_call, "name", ""),
                            tool_input=json.dumps(dict(getattr(fn_call, "args", {}) or {})),
                        )
        yield StreamEvent(type=StreamEventType.DONE)


# ── Factory ───────────────────────────────────────────────────────────

def _require_key(provider: str, api_key: str | None) -> str:
    if api_key is not None and api_key.strip() != "":
        return api_key
    key_names = {
        "openai": "OPENAI_API_KEY (or KAGEKO_API_KEY)",
        "deepseek": "DEEPSEEK_API_KEY (or KAGEKO_API_KEY)",
        "claude": "CLAUDE_API_KEY / ANTHROPIC_API_KEY (or KAGEKO_API_KEY)",
        "gemini": "GEMINI_API_KEY / GOOGLE_API_KEY (or KAGEKO_API_KEY)",
    }
    raise ValueError(
        f"Missing API key for {provider}. Set {key_names.get(provider, 'KAGEKO_API_KEY')} "
        "or pass api_key to create_runtime()."
    )


def create_llm_adapter(
    *,
    provider: str,
    api_key: str | None,
    model: str | None,
    base_url: str | None,
):
    normalized = provider.strip().lower()

    if normalized == "openai":
        from openai import OpenAI
        key = _require_key(normalized, api_key)
        resolved_model = model or "gpt-4.1-mini"
        return OpenAIAdapter(
            client=OpenAI(api_key=key, base_url=base_url),
            model=resolved_model,
        )

    if normalized == "deepseek":
        from openai import OpenAI
        key = _require_key(normalized, api_key)
        resolved_model = model or "deepseek-chat"
        resolved_base_url = base_url or "https://api.deepseek.com/v1"
        return OpenAIAdapter(
            client=OpenAI(api_key=key, base_url=resolved_base_url),
            model=resolved_model,
        )

    if normalized == "claude":
        from anthropic import Anthropic
        key = _require_key(normalized, api_key)
        resolved_model = model or "claude-sonnet-4-6"
        return AnthropicAdapter(
            client=Anthropic(api_key=key),
            model=resolved_model,
        )

    if normalized == "gemini":
        from google import genai
        key = _require_key(normalized, api_key)
        resolved_model = model or "gemini-2.5-flash"
        return GeminiAdapter(
            client=genai.Client(api_key=key),
            model=resolved_model,
        )

    raise ValueError(
        f"Unsupported provider '{provider}'. "
        "Supported: openai, deepseek, claude, gemini."
    )
