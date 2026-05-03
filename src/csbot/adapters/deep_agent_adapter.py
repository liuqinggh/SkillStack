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

    def _resolve_agent_id(self, agent_id: str | None) -> str:
        return (agent_id or self._settings.agent.default_profile_id).strip() or self._settings.agent.default_profile_id

    @lru_cache(maxsize=None)
    def _runtime_for_agent(self, agent_id: str) -> DeepAgentsRuntime:
        profile = self._settings.agent.resolve_profile(agent_id)
        return DeepAgentsRuntime(self._settings, self._provider, profile=profile, agent_id=agent_id)

    def run_turn(self, user_input: str, session_id: str, *, agent_id: str | None = None) -> str:
        return self._runtime_for_agent(self._resolve_agent_id(agent_id)).run_turn(user_input, session_id)

    def run_stream(self, user_input: str, session_id: str, *, agent_id: str | None = None) -> Iterator[str]:
        yield from self._runtime_for_agent(self._resolve_agent_id(agent_id)).iter_stream_deltas(user_input, session_id)

    def iter_stream_deltas(self, user_input: str, session_id: str, *, agent_id: str | None = None) -> Iterator[str]:
        yield from self.run_stream(user_input, session_id, agent_id=agent_id)
