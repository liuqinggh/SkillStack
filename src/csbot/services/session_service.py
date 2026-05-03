from __future__ import annotations

import uuid

from csbot.domain.models import SessionRecord
from csbot.storage.jsonl_store import JsonlSessionStore


class SessionService:
    def __init__(self, store: JsonlSessionStore) -> None:
        self._store = store

    def append_turn(
        self,
        role: str,
        content: str,
        session_id: str,
        *,
        agent_id: str | None = None,
        thinking: str | None = None,
        files: list[dict[str, str | int | None]] | None = None,
    ) -> SessionRecord:
        try:
            normalized_session_id = str(uuid.UUID(session_id))
        except Exception as exc:
            raise ValueError(f"session_id must be UUID, got: {session_id}") from exc
        record = SessionRecord.create(
            role=role,
            content=content,
            session_id=normalized_session_id,
            agent_id=agent_id.strip() if isinstance(agent_id, str) and agent_id.strip() else None,
            thinking=thinking,
            files=files or [],
        )
        self._store.append(record)
        return record

    def list_session(self, session_id: str) -> list[SessionRecord]:
        return [r for r in self._store.read_all() if r.session_id == session_id]

    def list_all(self) -> list[SessionRecord]:
        return self._store.read_all()

    def delete_message(self, session_id: str, message_id: str) -> bool:
        rows = self._store.read_all()
        next_rows: list[SessionRecord] = []
        deleted = False
        for row in rows:
            if row.session_id == session_id and row.message_id == message_id:
                deleted = True
                continue
            next_rows.append(row)
        if deleted:
            self._store.replace_all(next_rows)
        return deleted

    def delete_session(self, session_id: str) -> None:
        rows = self._store.read_all()
        self._store.replace_all([r for r in rows if r.session_id != session_id])
