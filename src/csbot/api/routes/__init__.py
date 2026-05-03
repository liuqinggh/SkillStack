from __future__ import annotations

from fastapi import APIRouter

from csbot.api.deps import AppContext

from .agents import create_agents_router
from .auth import create_auth_router
from .conversations import create_conversations_router
from .health import create_health_router
from .messages import create_messages_router
from .root_static import create_root_static_router
from .runs import create_runs_router
from .sessions import create_sessions_router
from .uploads import create_uploads_router


def create_router(context: AppContext) -> APIRouter:
    router = APIRouter()
    router.include_router(create_health_router(context))
    router.include_router(create_auth_router(context))
    router.include_router(create_agents_router(context))
    router.include_router(create_conversations_router(context))
    router.include_router(create_messages_router(context))
    router.include_router(create_sessions_router(context))
    router.include_router(create_uploads_router(context))
    router.include_router(create_runs_router(context))
    router.include_router(create_root_static_router(context))
    return router
