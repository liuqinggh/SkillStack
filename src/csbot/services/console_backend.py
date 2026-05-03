from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import hashlib
import json

from csbot.config.settings import AgentProfileConfig


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TokenRecord:
    token: str
    user_id: str
    expires_at: datetime


@dataclass
class AuthUser:
    id: str
    email: str
    name: str


class AuthService:
    def __init__(self, *, admin_email: str, password_hash: str, admin_name: str, access_ttl_minutes: int = 720) -> None:
        self._admin_email = admin_email
        self._password_hash = password_hash
        self._admin_name = admin_name
        self._ttl = max(1, access_ttl_minutes)
        self._tokens: dict[str, TokenRecord] = {}

    def admin_user(self) -> AuthUser:
        return AuthUser(id='admin', email=self._admin_email, name=self._admin_name)

    def login(self, email: str, password: str) -> tuple[AuthUser, str] | None:
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if email.strip().lower() != self._admin_email.lower() or password_hash != self._password_hash:
            return None
        user = self.admin_user()
        token = str(uuid4())
        self._tokens[token] = TokenRecord(
            token=token,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=self._ttl),
        )
        return user, token

    def resolve(self, token: str | None) -> AuthUser | None:
        if not token:
            return None
        rec = self._tokens.get(token)
        if rec is None:
            return None
        if rec.expires_at <= datetime.now(timezone.utc):
            self._tokens.pop(token, None)
            return None
        return self.admin_user()


@dataclass
class AgentRecord:
    _id: str
    name: str
    hermesProfile: str
    createdAt: str
    updatedAt: str
    model: str | None
    exists: bool
    dailyCapUsd: float | None
    monthlyCapUsd: float | None
    allTimeCapUsd: float | None


@dataclass
class ConversationRecord:
    _id: str
    agentId: str
    title: str | None
    sessionKey: str | None
    createdAt: str
    updatedAt: str
    session_settings: dict[str, Any] = field(default_factory=dict)


class AgentService:
    def __init__(
        self,
        profiles: dict[str, AgentProfileConfig],
        *,
        default_profile_id: str,
        default_model: str,
    ) -> None:
        ts = now_iso()
        self._configured_profile_ids = set(profiles)
        self._agents: dict[str, AgentRecord] = {}
        for profile_id in profiles:
            self._agents[profile_id] = AgentRecord(
                _id=profile_id,
                name=self._display_name_for_profile(profile_id, default_profile_id),
                hermesProfile=profile_id,
                createdAt=ts,
                updatedAt=ts,
                model=default_model,
                exists=True,
                dailyCapUsd=None,
                monthlyCapUsd=None,
                allTimeCapUsd=None,
            )

    @staticmethod
    def _display_name_for_profile(profile_id: str, default_profile_id: str) -> str:
        if profile_id == default_profile_id:
            return 'Default Agent'
        words = profile_id.replace('-', ' ').replace('_', ' ').split()
        if not words:
            return profile_id
        return ' '.join(part.capitalize() for part in words)

    def list(self) -> list[AgentRecord]:
        return list(self._agents.values())

    def get(self, agent_id: str) -> AgentRecord | None:
        return self._agents.get(agent_id)

    def create(self, name: str, hermes_profile: str | None = None) -> AgentRecord | None:
        _ = name
        profile_id = (hermes_profile or '').strip()
        if not profile_id:
            return None
        return self._agents.get(profile_id)

    def update(self, agent_id: str, payload: dict[str, Any]) -> AgentRecord | None:
        row = self._agents.get(agent_id)
        if row is None:
            return None
        row.name = str(payload.get('name', row.name))
        if 'dailyCapUsd' in payload:
            row.dailyCapUsd = payload.get('dailyCapUsd')
        if 'monthlyCapUsd' in payload:
            row.monthlyCapUsd = payload.get('monthlyCapUsd')
        if 'allTimeCapUsd' in payload:
            row.allTimeCapUsd = payload.get('allTimeCapUsd')
        row.updatedAt = now_iso()
        return row

    def delete(self, agent_id: str) -> bool:
        if agent_id in self._configured_profile_ids:
            return False
        return self._agents.pop(agent_id, None) is not None


class ConversationService:
    def __init__(self, storage_path: str | None = None) -> None:
        self._rows: dict[str, ConversationRecord] = {}
        self._storage_path = Path(storage_path).resolve() if storage_path else None
        self._load()

    def list_all(self) -> list[ConversationRecord]:
        return sorted(self._rows.values(), key=lambda r: r.createdAt)

    def list_by_agent(self, agent_id: str) -> list[ConversationRecord]:
        return [r for r in self.list_all() if r.agentId == agent_id]

    def get(self, conversation_id: str) -> ConversationRecord | None:
        return self._rows.get(conversation_id)

    def create(self, conversation_id: str, agent_id: str) -> ConversationRecord:
        ts = now_iso()
        row = ConversationRecord(
            _id=conversation_id,
            agentId=agent_id,
            title=None,
            sessionKey=conversation_id,
            createdAt=ts,
            updatedAt=ts,
        )
        self._rows[conversation_id] = row
        self._persist()
        return row

    def ensure(self, conversation_id: str, agent_id: str) -> ConversationRecord:
        row = self._rows.get(conversation_id)
        if row is None:
            row = self.create(conversation_id, agent_id)
        elif row.agentId != agent_id:
            raise ValueError(f'Conversation {conversation_id} already belongs to agent {row.agentId}')
        return row

    def rename(self, conversation_id: str, title: str) -> ConversationRecord | None:
        row = self._rows.get(conversation_id)
        if row is None:
            return None
        row.title = title
        row.updatedAt = now_iso()
        self._persist()
        return row

    def delete(self, conversation_id: str) -> bool:
        deleted = self._rows.pop(conversation_id, None) is not None
        if deleted:
            self._persist()
        return deleted

    def get_settings(self, conversation_id: str) -> dict[str, Any]:
        row = self._rows.get(conversation_id)
        if row is None:
            return {}
        return row.session_settings

    def patch_settings(self, conversation_id: str, updates: dict[str, Any]) -> bool:
        row = self._rows.get(conversation_id)
        if row is None:
            return False
        row.session_settings.update({k: v for k, v in updates.items() if v is not None})
        row.updatedAt = now_iso()
        self._persist()
        return True

    def bootstrap_from_transcripts(
        self,
        session_rows: dict[str, list[Any]],
        *,
        default_agent_id: str,
    ) -> None:
        changed = False
        for session_id, messages in session_rows.items():
            if session_id in self._rows or not messages:
                continue
            first = messages[0]
            last = messages[-1]
            title = self._derive_title(messages)
            self._rows[session_id] = ConversationRecord(
                _id=session_id,
                agentId=default_agent_id,
                title=title,
                sessionKey=session_id,
                createdAt=getattr(first, 'ts', now_iso()),
                updatedAt=getattr(last, 'ts', now_iso()),
            )
            changed = True
        if changed:
            self._persist()

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.is_file():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding='utf-8'))
        except Exception:
            return
        if not isinstance(payload, list):
            return
        for item in payload:
            if not isinstance(item, dict):
                continue
            conversation_id = str(item.get('_id', '')).strip()
            agent_id = str(item.get('agentId', '')).strip()
            if not conversation_id or not agent_id:
                continue
            self._rows[conversation_id] = ConversationRecord(
                _id=conversation_id,
                agentId=agent_id,
                title=item.get('title') if isinstance(item.get('title'), str) else None,
                sessionKey=str(item.get('sessionKey') or conversation_id),
                createdAt=str(item.get('createdAt') or now_iso()),
                updatedAt=str(item.get('updatedAt') or now_iso()),
                session_settings=item.get('session_settings')
                if isinstance(item.get('session_settings'), dict)
                else {},
            )

    def _persist(self) -> None:
        if self._storage_path is None:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                '_id': row._id,
                'agentId': row.agentId,
                'title': row.title,
                'sessionKey': row.sessionKey,
                'createdAt': row.createdAt,
                'updatedAt': row.updatedAt,
                'session_settings': row.session_settings,
            }
            for row in self.list_all()
        ]
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    @staticmethod
    def _derive_title(messages: list[Any]) -> str | None:
        for row in messages:
            role = getattr(row, 'role', None)
            content = str(getattr(row, 'content', '')).strip()
            if role == 'user' and content:
                return content[:40]
        return None
