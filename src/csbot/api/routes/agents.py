from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from csbot.api.deps import AppContext
from .auth import _require_user


class CreateAgentBody(BaseModel):
    name: str
    hermesProfile: str | None = None


class UpdateAgentBody(BaseModel):
    name: str | None = None
    dailyCapUsd: float | None = None
    monthlyCapUsd: float | None = None
    allTimeCapUsd: float | None = None


def create_agents_router(context: AppContext) -> APIRouter:
    router = APIRouter(prefix='/api/agent', tags=['agent'])

    @router.get('')
    def get_agents(authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        items = [r.__dict__ for r in context.agent_service.list()]
        return {'total': len(items), 'items': items}

    @router.get('/{agent_id}')
    def get_agent(agent_id: str, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        row = context.agent_service.get(agent_id)
        if row is None:
            raise HTTPException(status_code=404, detail='Agent not found')
        return row.__dict__

    @router.post('')
    def create_agent(payload: CreateAgentBody, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        row = context.agent_service.create(payload.name, payload.hermesProfile)
        if row is None:
            raise HTTPException(
                status_code=400,
                detail='Agents are managed by conf.yaml profiles; create is not supported for unknown profiles',
            )
        return row.__dict__

    @router.patch('/{agent_id}')
    def update_agent(agent_id: str, payload: UpdateAgentBody, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        row = context.agent_service.update(agent_id, payload.model_dump(exclude_none=False))
        if row is None:
            raise HTTPException(status_code=404, detail='Agent not found')
        return row.__dict__

    @router.delete('/{agent_id}', status_code=204)
    def delete_agent(agent_id: str, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        if not context.agent_service.delete(agent_id):
            raise HTTPException(status_code=404, detail='Agent not found')

    @router.post('/sync')
    def sync_agents(authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        return {'syncedAgents': 0, 'syncedConversations': 0, 'syncedMessages': 0}

    @router.get('/{agent_id}/conversation/{conversation_id}/session-settings')
    def get_session_settings(agent_id: str, conversation_id: str, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        if context.agent_service.get(agent_id) is None:
            raise HTTPException(status_code=404, detail='Agent not found')
        row = context.conversation_service.get(conversation_id)
        if row is None:
            raise HTTPException(status_code=404, detail='Conversation not found')
        if row.agentId != agent_id:
            raise HTTPException(status_code=400, detail='Conversation does not belong to the specified agent')
        return {
            'ok': True,
            'settings': {
                'thinkingLevel': row.session_settings.get('thinkingLevel', 'auto'),
                'fastMode': row.session_settings.get('fastMode', None),
                'verboseLevel': row.session_settings.get('verboseLevel', 'normal'),
                'reasoningLevel': row.session_settings.get('reasoningLevel', 'auto'),
            },
        }

    @router.patch('/{agent_id}/conversation/{conversation_id}/session-settings')
    def patch_session_settings(agent_id: str, conversation_id: str, payload: dict, authorization: str | None = Header(default=None, alias='Authorization')):
        _require_user(context, authorization)
        if context.agent_service.get(agent_id) is None:
            raise HTTPException(status_code=404, detail='Agent not found')
        row = context.conversation_service.get(conversation_id)
        if row is None:
            raise HTTPException(status_code=404, detail='Conversation not found')
        if row.agentId != agent_id:
            raise HTTPException(status_code=400, detail='Conversation does not belong to the specified agent')
        if not context.conversation_service.patch_settings(conversation_id, payload):
            raise HTTPException(status_code=404, detail='Conversation not found')
        return {'ok': True}

    return router
