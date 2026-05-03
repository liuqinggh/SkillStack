from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入内容")
    session_id: str | None = Field(default=None, description="会话 ID（UUID），同 ID 保持多轮上下文")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="助手回复")
    session_id: str = Field(..., description="会话 ID（UUID）")


class StreamEvent(BaseModel):
    type: str = Field(..., description="delta|done|error")
    session_id: str
    delta: str | None = None
    reply: str | None = None
    error: str | None = None


@dataclass(slots=True)
class SessionRecord:
    message_id: str
    role: str
    content: str
    session_id: str
    ts: str
    thinking: str | None = None
    files: list[dict[str, Any]] | None = None

    @classmethod
    def create(
        cls,
        *,
        role: str,
        content: str,
        session_id: str,
        thinking: str | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> SessionRecord:
        return cls(
            message_id=str(uuid4()),
            role=role,
            content=content,
            session_id=session_id,
            ts=datetime.now(timezone.utc).isoformat(),
            thinking=thinking,
            files=files or [],
        )

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> SessionRecord:
        raw_session_id = payload.get("session_id") or payload.get("thread_id")
        try:
            parsed_session_id = str(uuid.UUID(str(raw_session_id)))
        except Exception:
            if raw_session_id:
                parsed_session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"legacy-session:{raw_session_id}"))
            else:
                parsed_session_id = str(uuid4())
        return cls(
            message_id=str(payload.get("message_id") or uuid4()),
            role=str(payload.get("role", "assistant")),
            content=str(payload.get("content", "")),
            session_id=parsed_session_id,
            ts=str(payload.get("ts") or datetime.now(timezone.utc).isoformat()),
            thinking=payload.get("thinking") if isinstance(payload.get("thinking"), str) else None,
            files=payload.get("files") if isinstance(payload.get("files"), list) else [],
        )
