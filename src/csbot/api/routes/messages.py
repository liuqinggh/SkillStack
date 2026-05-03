from __future__ import annotations

import inspect
import uuid
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from csbot.api.deps import AppContext
from csbot.api.sse_compat import from_runtime_event
from csbot.runtime.events import RuntimeEventDelta, RuntimeEventError
from csbot.runtime.service import RuntimeService
from csbot.uploads.service import AttachmentRow
from .auth import _require_user


def _to_message(row) -> dict[str, Any]:
    return {
        '_id': row.message_id,
        'conversationId': row.session_id,
        'text': row.content,
        'thinking': row.thinking,
        'files': row.files or [],
        'role': row.role,
        'createdAt': row.ts,
        'agentId': row.agent_id,
    }


def _paginate(items: list[dict[str, Any]], before: str | None, limit: int = 30):
    if before:
        older = [m for m in items if m['createdAt'] < before]
        chunk = older[-limit:]
        return chunk, len(older) > len(chunk)
    chunk = items[-limit:]
    return chunk, len(items) > len(chunk)


def _supports_agent_id_kwarg(method: object) -> bool:
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return False
    if 'agent_id' in signature.parameters:
        return True
    return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())


def _engine_stream_adapter(engine: object) -> object:
    class _Adapter:
        def iter_stream_deltas(
            self,
            user_input: str,
            session_id: str,
            *,
            agent_id: str | None = None,
        ) -> Iterator[str]:
            rs = getattr(engine, 'iter_stream_deltas', None)
            if callable(rs):
                if agent_id is not None and _supports_agent_id_kwarg(rs):
                    yield from rs(user_input, session_id, agent_id=agent_id)
                else:
                    yield from rs(user_input, session_id)
                return
            run_stream = getattr(engine, 'run_stream', None)
            if callable(run_stream):
                if agent_id is not None and _supports_agent_id_kwarg(run_stream):
                    yield from run_stream(user_input, session_id, agent_id=agent_id)
                else:
                    yield from run_stream(user_input, session_id)
                return
            raise TypeError('engine must expose iter_stream_deltas or run_stream')

    return _Adapter()


def create_messages_router(context: AppContext) -> APIRouter:
    router = APIRouter(prefix='/api/message', tags=['message'])

    @router.get('/conversation/{conversation_id}')
    def get_messages(
        conversation_id: str,
        before: str | None = None,
        authorization: str | None = Header(default=None, alias='Authorization'),
    ):
        _require_user(context, authorization)
        if context.conversation_service.get(conversation_id) is None:
            raise HTTPException(status_code=404, detail='Conversation not found')
        rows = context.transcript_service.list_session(conversation_id)
        items = [_to_message(r) for r in rows]
        page, has_more = _paginate(items, before)
        return {'total': len(items), 'items': page, 'hasMore': has_more}

    @router.get('/conversation/{conversation_id}/poll')
    def poll_messages(
        conversation_id: str,
        after: str | None = None,
        authorization: str | None = Header(default=None, alias='Authorization'),
    ):
        _require_user(context, authorization)
        if context.conversation_service.get(conversation_id) is None:
            raise HTTPException(status_code=404, detail='Conversation not found')
        rows = context.transcript_service.list_session(conversation_id)
        items = [_to_message(r) for r in rows]
        if after:
            items = [m for m in items if m['createdAt'] > after]
        return {'items': items, 'synced': len(items)}

    @router.post('')
    def create_message(payload: dict, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        conversation_id = str(payload.get('conversationId', '')).strip()
        if not conversation_id:
            raise HTTPException(status_code=400, detail='conversationId is required')
        conversation = context.conversation_service.get(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail='Conversation not found')
        row = context.transcript_service.append_turn(
            role='user',
            content=str(payload.get('text', '')).strip(),
            session_id=conversation_id,
            agent_id=conversation.agentId,
        )
        return _to_message(row)

    @router.delete('/{message_id}', status_code=204)
    def delete_message(message_id: str, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        deleted = False
        for conv in context.conversation_service.list_all():
            if context.transcript_service.delete_message(conv._id, message_id):
                deleted = True
                break
        if not deleted:
            raise HTTPException(status_code=404, detail='Message not found')

    @router.post('/chat')
    async def chat(
        conversationId: str = Form(...),
        text: str = Form(''),
        files: list[UploadFile] = File(default_factory=list),
        authorization: str | None = Header(default=None, alias='Authorization'),
    ):
        _require_user(context, authorization)
        conversation = context.conversation_service.get(conversationId)
        if conversation is None:
            raise HTTPException(status_code=404, detail='Conversation not found')
        agent_id = conversation.agentId
        if context.agent_service.get(agent_id) is None:
            raise HTTPException(status_code=400, detail='Conversation points to an unknown agent')

        attachment_rows: list[AttachmentRow] = []
        file_payloads: list[dict[str, Any]] = []
        for file in files:
            content = await file.read()
            row = context.uploads_service.save_attachment(
                session_id=conversationId,
                filename=file.filename or 'upload.bin',
                media_type=file.content_type or 'application/octet-stream',
                content=content,
                ocr_mode='auto',
            )
            attachment_rows.append(row)
            file_payloads.append(
                {
                    'filename': row.filename,
                    'originalName': row.filename,
                    'mimetype': row.media_type,
                    'size': row.size_bytes,
                    'url': row.stored_path,
                }
            )

        user_text = text.strip()
        if not user_text and not file_payloads:
            raise HTTPException(status_code=400, detail='text or files is required')

        context.transcript_service.append_turn(
            role='user',
            content=user_text,
            session_id=conversationId,
            agent_id=agent_id,
            files=file_payloads,
        )

        runtime = RuntimeService(
            context.settings,
            _engine_stream_adapter(context.engine),
            uploads_service=context.uploads_service,
            transcript_service=None,
        )
        run_id = str(uuid.uuid4())

        def event_stream():
            reply = ''
            for evt in runtime.stream_run(
                message=user_text,
                attachments=attachment_rows,
                run_id=run_id,
                session_id=conversationId,
                session_stream_id=conversationId,
                agent_id=agent_id,
            ):
                line = from_runtime_event(evt)
                if line:
                    yield line
                if isinstance(evt, RuntimeEventDelta):
                    reply += evt.delta
                if isinstance(evt, RuntimeEventError):
                    yield 'data: [DONE]\n\n'
                    return
            context.transcript_service.append_turn(
                role='assistant',
                content=reply or '(无回复)',
                session_id=conversationId,
                agent_id=agent_id,
            )
            yield 'data: [DONE]\n\n'

        return StreamingResponse(event_stream(), media_type='text/event-stream')

    return router
