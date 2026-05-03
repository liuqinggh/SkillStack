from __future__ import annotations

from dataclasses import dataclass

from csbot.sessions.repository import SessionRepository


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    latest_run_id: str | None
    agent_id: str | None = None


class SessionsService:
    """Runtime session lifecycle (metadata); separate from legacy Jsonl chat turns."""

    def __init__(self, repository: SessionRepository) -> None:
        self._repo = repository

    def create_session(self) -> str:
        return self._repo.create()

    def get_summary(self, session_id: str) -> SessionSummary | None:
        row = self._repo.get(session_id)
        if row is None:
            return None
        return SessionSummary(session_id=row.session_id, latest_run_id=row.latest_run_id, agent_id=row.agent_id)

    def record_latest_run(self, session_id: str, run_id: str) -> None:
        self._repo.set_latest_run(session_id, run_id)

    def bind_agent(self, session_id: str, agent_id: str) -> bool:
        return self._repo.bind_agent(session_id, agent_id)
