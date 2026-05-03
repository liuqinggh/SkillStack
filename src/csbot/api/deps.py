from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache

from csbot.adapters.deep_agent_adapter import DeepAgentAdapter
from csbot.config.settings import DEFAULT_DB_PATH, Settings, load_settings
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


def build_context(db_path: str = DEFAULT_DB_PATH) -> AppContext:
    settings = load_settings(db_path)

    store = JsonlSessionStore(settings.storage.session_jsonl_path)
    transcript_service = SessionService(store)
    sessions_repository = InMemorySessionRepository()
    sessions_service = SessionsService(sessions_repository)
    uploads_service = UploadsService(settings, InMemoryAttachmentRepository())
    engine = DeepAgentAdapter(settings)
    auth_service = AuthService(
        admin_email=settings.auth.admin_email,
        password_hash=settings.auth.password_hash,
        admin_name=settings.auth.admin_name,
        access_ttl_minutes=settings.auth.access_ttl_minutes,
    )
    agent_service = AgentService(
        settings.agent.profiles,
        default_profile_id=settings.agent.default_profile_id,
        default_model=settings.llm.model,
    )
    conversation_storage_path = settings.project_root / 'data' / 'conversations.json'
    conversation_service = ConversationService(str(conversation_storage_path))
    session_rows: dict[str, list[object]] = {}
    for row in transcript_service.list_all():
        session_rows.setdefault(row.session_id, []).append(row)
    conversation_service.bootstrap_from_transcripts(
        session_rows,
        default_agent_id=settings.agent.default_profile_id,
    )
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
def get_context(db_path: str = DEFAULT_DB_PATH) -> AppContext:
    return build_context(db_path)
