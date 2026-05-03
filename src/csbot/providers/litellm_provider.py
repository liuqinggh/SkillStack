from __future__ import annotations

from typing import Any

from csbot.config.settings import LlmConfig
from csbot.providers.base import LlmProvider


class LiteLLMProvider(LlmProvider):
    """Maps app LLM config to kwargs suitable for an OpenAI-compatible endpoint (e.g. LiteLLM proxy)."""

    def __init__(self, config: LlmConfig) -> None:
        super().__init__(config)
        if config.provider != "litellm":
            raise ValueError(f"LiteLLMProvider requires llm.provider='litellm', got {config.provider!r}")

    def openai_compatible_model_kwargs(self) -> dict[str, Any]:
        c = self._config
        return {
            "model": c.model,
            "base_url": c.base_url,
            "api_key": c.api_key,
            "temperature": c.temperature,
            "timeout": c.timeout_sec,
            "max_tokens": c.max_tokens,
        }
