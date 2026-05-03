"""Runtime correlation context (single run; no HTTP or persistence)."""

from __future__ import annotations

from dataclasses import dataclass

from csbot.config.settings import Settings
from csbot.providers.base import LlmProvider


@dataclass(frozen=True)
class RuntimeContext:
    settings: Settings
    llm_provider: LlmProvider
    run_id: str
    session_id: str | None
    session_stream_id: str
