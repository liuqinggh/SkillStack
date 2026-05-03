from __future__ import annotations

from fastapi import APIRouter, HTTPException

from csbot.api.deps import AppContext
from csbot.api.schemas.session import SessionSummary as SessionSummarySchema


def create_sessions_router(context: AppContext) -> APIRouter:
    router = APIRouter(prefix="/api/runtime", tags=["sessions"])

    @router.post("/sessions", response_model=SessionSummarySchema)
    def create_session() -> SessionSummarySchema:
        session_id = context.sessions_service.create_session()
        return SessionSummarySchema(session_id=session_id, latest_run_id=None)

    @router.get("/sessions/{session_id}", response_model=SessionSummarySchema)
    def get_session(session_id: str) -> SessionSummarySchema:
        row = context.sessions_service.get_summary(session_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionSummarySchema(session_id=row.session_id, latest_run_id=row.latest_run_id)

    return router
