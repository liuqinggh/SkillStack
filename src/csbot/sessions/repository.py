from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import uuid

from csbot.domain.errors import SessionNotFoundError


@dataclass(frozen=True)
class SessionRow:
    session_id: str
    latest_run_id: str | None = None
    agent_id: str | None = None


class SessionRepository(Protocol):
    def create(self) -> str: ...
    def get(self, session_id: str) -> SessionRow | None: ...
    def set_latest_run(self, session_id: str, run_id: str) -> None: ...
    def bind_agent(self, session_id: str, agent_id: str) -> bool: ...


class InMemorySessionRepository:
    """Process-local session metadata store (phase 1; replace with durable backend later)."""

    def __init__(self) -> None:
        self._rows: dict[str, SessionRow] = {}

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        self._rows[session_id] = SessionRow(session_id=session_id)
        return session_id

    def get(self, session_id: str) -> SessionRow | None:
        return self._rows.get(session_id)

    def set_latest_run(self, session_id: str, run_id: str) -> None:
        row = self._rows.get(session_id)
        if row is None:
            raise SessionNotFoundError(session_id)
        self._rows[session_id] = SessionRow(
            session_id=session_id,
            latest_run_id=run_id,
            agent_id=row.agent_id,
        )

    def bind_agent(self, session_id: str, agent_id: str) -> bool:
        row = self._rows.get(session_id)
        if row is None:
            raise SessionNotFoundError(session_id)
        if row.agent_id is not None and row.agent_id != agent_id:
            return False
        if row.agent_id == agent_id:
            return True
        self._rows[session_id] = SessionRow(
            session_id=session_id,
            latest_run_id=row.latest_run_id,
            agent_id=agent_id,
        )
        return True
