"""Session-related API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SessionSummary(BaseModel):
    session_id: str = Field(..., description="Public session identifier")
    latest_run_id: str | None = Field(default=None, description="Most recent run on this session, if any")
