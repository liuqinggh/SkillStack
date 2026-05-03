"""Shared API schema types."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorEnvelope(BaseModel):
    code: str = Field(..., description="Machine-readable error category")
    message: str = Field(..., description="Human-readable error summary")
    run_id: str | None = Field(default=None, description="Associated run, if known")
    session_id: str | None = Field(default=None, description="Associated session, if known")
    retryable: bool = Field(default=False, description="Whether the client may retry safely")
    details: dict[str, object] | None = Field(default=None, description="Optional structured detail")
