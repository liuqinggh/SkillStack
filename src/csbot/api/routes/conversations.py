from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from csbot.api.deps import AppContext
from .auth import _require_user


class CreateConversationBody(BaseModel):
    agentId: str


class UpdateConversationBody(BaseModel):
    title: str



def create_conversations_router(context: AppContext) -> APIRouter:
    router = APIRouter(prefix='/api/conversation', tags=['conversation'])

    @router.get('')
    def get_all_conversations(authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        items = [r.__dict__ for r in context.conversation_service.list_all()]
        return {'total': len(items), 'items': items}

    @router.get('/agent/{agent_id}')
    def get_conversations_by_agent(agent_id: str, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        items = [r.__dict__ for r in context.conversation_service.list_by_agent(agent_id)]
        return {'total': len(items), 'items': items}

    @router.post('')
    def create_conversation(payload: CreateConversationBody, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        if context.agent_service.get(payload.agentId) is None:
            raise HTTPException(status_code=404, detail='Agent not found')
        session_id = context.sessions_service.create_session()
        row = context.conversation_service.create(session_id, payload.agentId)
        return row.__dict__

    @router.patch('/{conversation_id}')
    def update_conversation(conversation_id: str, payload: UpdateConversationBody, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        row = context.conversation_service.rename(conversation_id, payload.title)
        if row is None:
            raise HTTPException(status_code=404, detail='Conversation not found')
        return row.__dict__

    @router.delete('/{conversation_id}', status_code=204)
    def delete_conversation(conversation_id: str, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        if not context.conversation_service.delete(conversation_id):
            raise HTTPException(status_code=404, detail='Conversation not found')
        context.transcript_service.delete_session(conversation_id)

    return router
