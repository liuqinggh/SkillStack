from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from csbot.agents.deepagents_runtime import DeepAgentsRuntime
from csbot.config.settings import Settings
from csbot.providers.base import LlmProvider
from csbot.providers.litellm_provider import LiteLLMProvider


class DeepAgentAdapter:
    def __init__(self, settings: Settings, *, llm_provider: LlmProvider | None = None) -> None:
        self._settings = settings
        self._provider = llm_provider if llm_provider is not None else LiteLLMProvider(settings.llm)

    @lru_cache(maxsize=1)
    def _deployment_runtime(self) -> DeepAgentsRuntime:
        profile = self._settings.agent.deployment_profile()
        return DeepAgentsRuntime(self._settings, self._provider, profile=profile)

    def run_turn(self, user_input: str, session_id: str, *, agent_id: str | None = None) -> str:
        """agent_id 保留为兼容旧调用方；单 Agent 部署下始终使用 deployment_profile。"""
        return self._deployment_runtime().run_turn(user_input, session_id)

    def run_stream(self, user_input: str, session_id: str, *, agent_id: str | None = None) -> Iterator[str]:
        yield from self._deployment_runtime().iter_stream_deltas(user_input, session_id)

    def iter_stream_deltas(self, user_input: str, session_id: str, *, agent_id: str | None = None) -> Iterator[str]:
        yield from self.run_stream(user_input, session_id, agent_id=agent_id)
