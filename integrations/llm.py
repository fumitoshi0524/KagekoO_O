"""LLM adapters and provider selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI


@dataclass(slots=True, kw_only=True)
class LocalEchoModel:
    model_name: str = "local-echo"

    def generate(self, prompt: str) -> str:
        return f"[{self.model_name}] {prompt.strip()}"


@dataclass(slots=True, kw_only=True)
class EchoModelAdapter:
    model: LocalEchoModel

    def complete(self, prompt: str) -> str:
        return self.model.generate(prompt)


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


def _require_key(provider: str, api_key: str | None) -> str:
    if api_key is not None and api_key.strip() != "":
        return api_key
    key_name = "OPENAI_API_KEY (or KAGEKO_API_KEY)"
    if provider == "deepseek":
        key_name = "DEEPSEEK_API_KEY (or KAGEKO_API_KEY)"
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

    if normalized == "local":
        local_model = model or "local-echo"
        return EchoModelAdapter(model=LocalEchoModel(model_name=local_model))

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

    raise ValueError(
        f"Unsupported provider '{provider}'. Supported providers: openai, deepseek, local."
    )
