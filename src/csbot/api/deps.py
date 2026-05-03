from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache

import yaml

from csbot.adapters.deep_agent_adapter import DeepAgentAdapter
from csbot.config.settings import Settings, load_settings
from csbot.services.console_backend import AgentService, AuthService, ConversationService
from csbot.services.session_service import SessionService
from csbot.sessions.repository import InMemorySessionRepository
from csbot.sessions.service import SessionsService
from csbot.storage.jsonl_store import JsonlSessionStore
from csbot.uploads.service import InMemoryAttachmentRepository, UploadsService

RUNTIME_SERVICE_ID = 'demo-csbot-runtime'


@dataclass(frozen=True)
class AppContext:
    settings: Settings
    engine: DeepAgentAdapter
    transcript_service: SessionService
    sessions_service: SessionsService
    uploads_service: UploadsService
    auth_service: AuthService
    agent_service: AgentService
    conversation_service: ConversationService
    executor: ThreadPoolExecutor


def build_context(conf_path: str = 'conf.yaml') -> AppContext:
    settings = load_settings(conf_path)

    store = JsonlSessionStore(settings.storage.session_jsonl_path)
    transcript_service = SessionService(store)
    sessions_repository = InMemorySessionRepository()
    sessions_service = SessionsService(sessions_repository)
    uploads_service = UploadsService(settings, InMemoryAttachmentRepository())
    engine = DeepAgentAdapter(settings)
    auth_cfg: dict[str, object] = {}
    try:
        raw = yaml.safe_load(settings.conf_path.read_text(encoding='utf-8')) or {}
        if isinstance(raw, dict) and isinstance(raw.get('auth'), dict):
            auth_cfg = raw['auth']
    except Exception:
        auth_cfg = {}

    auth_raw = getattr(settings, 'auth', None)
    auth_service = AuthService(
        admin_email=str(auth_cfg.get('admin_email', getattr(auth_raw, 'admin_email', 'admin@admin.com'))),
        admin_password=str(auth_cfg.get('admin_password', getattr(auth_raw, 'admin_password', '123456'))),
        admin_name=str(auth_cfg.get('admin_name', getattr(auth_raw, 'admin_name', 'Admin'))),
        access_ttl_minutes=int(auth_cfg.get('access_ttl_minutes', getattr(auth_raw, 'access_ttl_minutes', 720))),
    )
    agent_service = AgentService(
        settings.agent.profiles,
        default_profile_id=settings.agent.default_profile_id,
        default_model=settings.llm.model,
    )
    conversation_service = ConversationService()
    executor = ThreadPoolExecutor(max_workers=settings.agent.thread_pool_workers)

    return AppContext(
        settings=settings,
        engine=engine,
        transcript_service=transcript_service,
        sessions_service=sessions_service,
        uploads_service=uploads_service,
        auth_service=auth_service,
        agent_service=agent_service,
        conversation_service=conversation_service,
        executor=executor,
    )


@lru_cache(maxsize=2)
def get_context(conf_path: str = 'conf.yaml') -> AppContext:
    return build_context(conf_path)
