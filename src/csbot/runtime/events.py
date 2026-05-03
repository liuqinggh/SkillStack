"""Normalized runtime event types for agent execution (SSE / internal stream)."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

RUNTIME_EVENT_TYPE_VALUES = frozenset(
    ("started", "planning", "delta", "tool_call", "tool_result", "done", "error")
)


class RuntimeEventStarted(BaseModel):
    type: Literal["started"] = "started"
    run_id: str
    session_id: str | None = None


class RuntimeEventPlanning(BaseModel):
    type: Literal["planning"] = "planning"
    run_id: str | None = None
    session_id: str | None = None


class RuntimeEventDelta(BaseModel):
    type: Literal["delta"] = "delta"
    delta: str
    run_id: str | None = None
    session_id: str | None = None


class RuntimeEventToolCall(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    name: str
    arguments: dict[str, object] | None = None
    run_id: str | None = None
    session_id: str | None = None


class RuntimeEventToolResult(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    name: str
    content: str | None = None
    run_id: str | None = None
    session_id: str | None = None


class RuntimeEventDone(BaseModel):
    type: Literal["done"] = "done"
    reply: str | None = None
    run_id: str | None = None
    session_id: str | None = None


class RuntimeEventError(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str | None = None
    run_id: str | None = None
    session_id: str | None = None


RuntimeEvent = Annotated[
    Union[
        RuntimeEventStarted,
        RuntimeEventPlanning,
        RuntimeEventDelta,
        RuntimeEventToolCall,
        RuntimeEventToolResult,
        RuntimeEventDone,
        RuntimeEventError,
    ],
    Field(discriminator="type"),
]
