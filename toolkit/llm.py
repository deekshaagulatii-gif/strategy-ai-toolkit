"""One small wrapper around the AI model, so the rest of the code never cares which provider is used.

Providers:
  anthropic     - Claude via the Anthropic API (ANTHROPIC_API_KEY)
  azure_openai  - a private Azure OpenAI deployment, for example in an EU region
                  (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT)

Neither is a free consumer chatbot. Check your provider's data terms before using any client data.
"""
from __future__ import annotations

import json
import os
import re
from typing import Protocol


class LLM(Protocol):
    def complete(self, prompt: str, max_tokens: int = 2000) -> str: ...


class AnthropicLLM:
    def __init__(self, model: str | None = None):
        import anthropic  # imported here so the tests run without the package

        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class AzureOpenAILLM:
    def __init__(self):
        from openai import AzureOpenAI

        self.client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
        self.deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        resp = self.client.chat.completions.create(
            model=self.deployment,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""


def get_llm() -> LLM:
    """Choose the provider from the LLM_PROVIDER setting in .env."""
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        return AnthropicLLM()
    if provider == "azure_openai":
        return AzureOpenAILLM()
    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use 'anthropic' or 'azure_openai'.")


def parse_json(text: str) -> dict:
    """Pull the JSON object out of a model reply, ignoring ``` fences or stray prose around it."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model reply did not contain a JSON object.")
    return json.loads(cleaned[start : end + 1])
