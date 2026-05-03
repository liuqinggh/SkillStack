from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from csbot.config.settings import LlmConfig


class LlmProvider(ABC):
    """Abstract LLM provider; concrete implementations map config to runtime/client inputs."""

    def __init__(self, config: LlmConfig) -> None:
        self._config = config

    @property
    def config(self) -> LlmConfig:
        return self._config

    @abstractmethod
    def openai_compatible_model_kwargs(self) -> dict[str, Any]:
        """Keyword arguments for OpenAI-compatible chat clients (e.g. langchain-openai ChatOpenAI)."""
