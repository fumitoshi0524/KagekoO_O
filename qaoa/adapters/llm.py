"""LLM adapters and provider selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anthropic import Anthropic
    from google.genai import Client as GeminiClient
    from openai import OpenAI


@dataclass(slots=True, kw_only=True)
class OpenAIResponsesAdapter:
    client: OpenAI
    model: str

    def complete(self, prompt: str) -> str:
        response = self.client.responses.create(model=self.model, input=prompt)
        output = response.output_text
        if output is None or output.strip() == "":
            raise RuntimeError("Provider returned an empty response.")
        return output


@dataclass(slots=True, kw_only=True)
class OpenAIChatCompletionsAdapter:
    client: OpenAI
    model: str

    def complete(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content if response.choices else None
        if content is None or content.strip() == "":
            raise RuntimeError("Provider returned an empty chat completion.")
        return content


@dataclass(slots=True, kw_only=True)
class AnthropicMessagesAdapter:
    client: Anthropic
    model: str
    max_tokens: int = 1024

    def complete(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        ]
        text = "\n".join(text_parts).strip()
        if text == "":
            raise RuntimeError("Provider returned an empty Claude response.")
        return text


@dataclass(slots=True, kw_only=True)
class GeminiGenerateContentAdapter:
    client: GeminiClient
    model: str

    def complete(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if text is None or text.strip() == "":
            collected: list[str] = []
            for candidate in getattr(response, "candidates", []) or []:
                content = getattr(candidate, "content", None)
                if content is None:
                    continue
                for part in getattr(content, "parts", []) or []:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        collected.append(part_text)
            text = "\n".join(collected).strip()
        if text is None or text.strip() == "":
            raise RuntimeError("Provider returned an empty Gemini response.")
        return text


def _require_key(provider: str, api_key: str | None) -> str:
    if api_key is not None and api_key.strip() != "":
        return api_key
    key_names = {
        "openai": "OPENAI_API_KEY (or KAGEKO_API_KEY)",
        "deepseek": "DEEPSEEK_API_KEY (or KAGEKO_API_KEY)",
        "claude": "CLAUDE_API_KEY / ANTHROPIC_API_KEY (or KAGEKO_API_KEY)",
        "gemini": "GEMINI_API_KEY / GOOGLE_API_KEY (or KAGEKO_API_KEY)",
    }
    key_name = key_names.get(provider, "KAGEKO_API_KEY")
    raise ValueError(
        f"Missing API key for {provider}. Set {key_name} or pass api_key to create_runtime()."
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
        return OpenAIResponsesAdapter(
            client=OpenAI(api_key=key, base_url=base_url),
            model=resolved_model,
        )

    if normalized == "deepseek":
        from openai import OpenAI

        key = _require_key(normalized, api_key)
        resolved_model = model or "deepseek-chat"
        resolved_base_url = base_url or "https://api.deepseek.com/v1"
        return OpenAIChatCompletionsAdapter(
            client=OpenAI(api_key=key, base_url=resolved_base_url),
            model=resolved_model,
        )

    if normalized == "claude":
        from anthropic import Anthropic

        key = _require_key(normalized, api_key)
        resolved_model = model or "claude-3-7-sonnet-latest"
        return AnthropicMessagesAdapter(
            client=Anthropic(api_key=key),
            model=resolved_model,
        )

    if normalized == "gemini":
        from google import genai

        key = _require_key(normalized, api_key)
        resolved_model = model or "gemini-2.5-flash"
        return GeminiGenerateContentAdapter(
            client=genai.Client(api_key=key),
            model=resolved_model,
        )

    raise ValueError(
        "Unsupported provider '{}'. Supported providers: openai, deepseek, claude, gemini.".format(
            provider
        )
    )
