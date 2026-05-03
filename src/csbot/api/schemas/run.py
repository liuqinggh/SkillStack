"""Run-related API schemas (requests, summaries, stream events)."""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

from csbot.runtime.events import RuntimeEvent

RunEvent: TypeAlias = RuntimeEvent

RunStatus = Literal[
    "queued",
    "running",
    "planning",
    "acting",
    "streaming",
    "succeeded",
    "failed",
    "cancelled",
]


class RunInput(BaseModel):
    message: str = Field(..., description="Primary user message or task text")
    attachments: list[str] = Field(default_factory=list, description="Uploaded attachment ids to include in this run")


class AgentSpec(BaseModel):
    id: str = Field(
        ...,
        description="Agent profile id declared in conf agent.profiles",
    )
    mode: str = Field(..., description="Execution mode (e.g. chat)")


class ModelSpec(BaseModel):
    provider: str = Field(default="litellm", description="Model routing provider")
    model: str = Field(..., description="Model name for the provider")


class RunRequest(BaseModel):
    input: RunInput
    agent: AgentSpec
    model: ModelSpec
    session_id: str | None = Field(default=None, description="Existing session to attach the run to")
    stream: bool = Field(default=True, description="Whether to stream execution events (e.g. SSE)")
    metadata: dict[str, str] | None = Field(default=None, description="Opaque client metadata")


class RunSummary(BaseModel):
    run_id: str = Field(..., description="Run identifier")
    status: RunStatus = Field(..., description="Current lifecycle status")
    session_id: str | None = Field(default=None, description="Session this run belongs to, if any")
