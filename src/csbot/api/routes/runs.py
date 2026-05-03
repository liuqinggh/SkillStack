from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from csbot.api.deps import AppContext
from csbot.api.schemas.run import RunRequest, RunStatus, RunSummary
from csbot.api.sse import format_sse_event
from csbot.domain.errors import SessionNotFoundError
from csbot.runtime.events import RuntimeEventDone, RuntimeEventError
from csbot.runtime.service import RuntimeService

logger = logging.getLogger(__name__)


def _session_stream_id_for_run(session_id: str | None, run_id: str) -> str:
    return session_id if session_id else run_id


def _engine_stream_adapter(engine: object) -> object:
    """Adapt DeepAgentAdapter (or test doubles) to RuntimeService protocol."""

    class _Adapter:
        def iter_stream_deltas(self, user_input: str, session_id: str) -> Iterator[str]:
            rs = getattr(engine, "iter_stream_deltas", None)
            if callable(rs):
                yield from rs(user_input, session_id)
                return
            run_stream = getattr(engine, "run_stream", None)
            if callable(run_stream):
                yield from run_stream(user_input, session_id)
                return
            raise TypeError("engine must expose iter_stream_deltas or run_stream")

    return _Adapter()


def create_runs_router(context: AppContext) -> APIRouter:
    router = APIRouter(prefix="/api/runtime", tags=["runs"])

    def resolve_attachments(session_id: str | None, attachment_ids: list[str]) -> list:
        rows = []
        for attachment_id in attachment_ids:
            row = context.uploads_service.get_attachment(attachment_id)
            if row is None:
                raise HTTPException(status_code=404, detail=f"Attachment not found: {attachment_id}")
            if session_id is None or row.session_id != session_id:
                raise HTTPException(status_code=400, detail="Attachment does not belong to the current session")
            rows.append(row)
        return rows

    @router.post("/runs", response_model=None)
    async def start_run(req: RunRequest):
        expected_agent_id = context.settings.agent.default_profile_id
        if req.agent.id != expected_agent_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "本部署为单 Agent 模式：请求体 agent.id 必须与配置 "
                    f"agent.default_profile_id 一致（期望 {expected_agent_id!r}，"
                    f"收到 {req.agent.id!r}）。"
                ),
            )

        if req.session_id is not None:
            if context.sessions_service.get_summary(req.session_id) is None:
                raise HTTPException(status_code=404, detail="Session not found")

        attachment_rows = resolve_attachments(req.session_id, req.input.attachments)
        run_id = str(uuid.uuid4())
        session_stream_id = _session_stream_id_for_run(req.session_id, run_id)
        runtime = RuntimeService(
            context.settings,
            _engine_stream_adapter(context.engine),
            uploads_service=context.uploads_service,
            transcript_service=context.transcript_service,
        )

        if req.stream:
            if not context.settings.stream.sse_enabled:
                raise HTTPException(status_code=404, detail="stream disabled")

            if req.session_id is not None:
                try:
                    context.sessions_service.record_latest_run(req.session_id, run_id)
                except SessionNotFoundError:
                    raise HTTPException(status_code=404, detail="Session not found") from None

            def event_generator():
                for ev in runtime.stream_run(
                    message=req.input.message,
                    attachments=attachment_rows,
                    run_id=run_id,
                    session_id=req.session_id,
                    session_stream_id=session_stream_id,
                ):
                    yield format_sse_event(ev)

            headers = {
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers=headers,
            )

        def collect_events():
            return list(
                runtime.stream_run(
                    message=req.input.message,
                    attachments=attachment_rows,
                    run_id=run_id,
                    session_id=req.session_id,
                    session_stream_id=session_stream_id,
                )
            )

        try:
            loop = asyncio.get_event_loop()
            timeout = context.settings.api.chat_timeout_sec
            events = await asyncio.wait_for(
                loop.run_in_executor(context.executor, collect_events),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "run timeout: run_id=%s after %ds",
                run_id,
                context.settings.api.chat_timeout_sec,
            )
            raise HTTPException(
                status_code=504,
                detail=(
                    f"请求处理超时（超过 {context.settings.api.chat_timeout_sec} 秒），请稍后重试或缩短输入。"
                ),
            ) from None

        if req.session_id is not None:
            try:
                context.sessions_service.record_latest_run(req.session_id, run_id)
            except SessionNotFoundError:
                raise HTTPException(status_code=404, detail="Session not found") from None

        last = events[-1] if events else None
        status: RunStatus
        if isinstance(last, RuntimeEventDone):
            status = "succeeded"
        elif isinstance(last, RuntimeEventError):
            status = "failed"
        else:
            status = "failed"

        return RunSummary(run_id=run_id, status=status, session_id=req.session_id)

    return router
