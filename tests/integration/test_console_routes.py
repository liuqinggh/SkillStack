"""Integration tests for Hermes-client compatibility routes."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot import create_app
from csbot.api.deps import AppContext, build_context, get_context
from csbot.config_repository.runtime_repository import RuntimeAgentConfigRecord, RuntimeAgentProfileRecord
from csbot.config_repository.seed import default_runtime_seed
from csbot.services.session_service import SessionService
from csbot.storage.jsonl_store import JsonlSessionStore
from tests.support.sqlite_config import write_runtime_db


class _FakeStreamEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def iter_stream_deltas(
        self,
        user_input: str,
        thread_id: str,
        *,
        agent_id: str | None = None,
    ) -> Iterator[str]:
        self.calls.append((user_input, thread_id, agent_id))
        yield 'hello'
        yield ' world'


def _write_multi_agent_db(path: Path) -> None:
    seed = default_runtime_seed(path.parent)
    seed = replace(
        seed,
        llm=replace(seed.llm, model='gpt-4', base_url='http://127.0.0.1:4000/v1', api_key='sk-test', temperature=0.5, timeout_sec=30, max_tokens=1000),
        agent=RuntimeAgentConfigRecord(
            skill_manager_root=str(path.parent.resolve()),
            thread_pool_workers=2,
            default_profile_id='default',
            profiles=[
                RuntimeAgentProfileRecord(
                    agent_id='default',
                    name='Default Agent',
                    system_prompt='default prompt',
                    memory_files=['default-memory.json'],
                    skills_sources=['skills'],
                    enabled=True,
                    is_default=True,
                ),
                RuntimeAgentProfileRecord(
                    agent_id='claim',
                    name='Claim',
                    system_prompt='claim prompt',
                    memory_files=['claim-memory.json'],
                    skills_sources=['skills'],
                    enabled=True,
                    is_default=False,
                ),
            ],
        ),
    )
    write_runtime_db(path, project_root=path.parent, seed=seed)


@pytest.fixture
def fake_context(tmp_path: Path) -> AppContext:
    get_context.cache_clear()
    db = write_runtime_db(tmp_path / 'db.sqlite', project_root=tmp_path)
    base = build_context(str(db))
    transcript = SessionService(JsonlSessionStore(str(tmp_path / 'console_transcript.jsonl')))
    return replace(base, engine=_FakeStreamEngine(), transcript_service=transcript)


def _login(client: TestClient) -> str:
    resp = client.post('/api/auth/login', json={'email': 'admin@admin.com', 'password': '123456'})
    assert resp.status_code == 200
    return resp.json()['accessToken']


def test_console_routes_and_chat_stream(fake_context: AppContext) -> None:
    app = create_app(str(fake_context.settings.bootstrap_db_path), app_context=fake_context)
    client = TestClient(app)

    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    assert client.get('/api/auth/token', headers=headers).status_code == 200
    assert client.get('/api/plugin', headers=headers).status_code == 200
    assert client.get('/api/skill', headers=headers).status_code == 200
    assert client.get('/api/cron', headers=headers).status_code == 200
    assert client.get('/api/insights', headers=headers).status_code == 200
    assert client.get('/api/update/status', headers=headers).status_code == 200

    agents = client.get('/api/agent', headers=headers)
    assert agents.status_code == 200
    items = agents.json()['items']
    assert items
    agent_id = items[0]['_id']

    created = client.post('/api/conversation', headers=headers, json={'agentId': agent_id})
    assert created.status_code == 200
    conversation_id = created.json()['_id']

    listed = client.get(f'/api/message/conversation/{conversation_id}', headers=headers)
    assert listed.status_code == 200
    assert listed.json()['total'] == 0

    stream = client.post(
        '/api/message/chat',
        headers=headers,
        data={'conversationId': conversation_id, 'text': 'hi'},
    )
    assert stream.status_code == 200
    assert 'text/event-stream' in stream.headers.get('content-type', '')
    body = stream.text
    assert 'response.output_text.delta' in body
    assert '[DONE]' in body

    polled = client.get(f'/api/message/conversation/{conversation_id}/poll', headers=headers)
    assert polled.status_code == 200
    assert polled.json()['synced'] >= 2
    assert fake_context.engine.calls[-1] == ('hi', conversation_id, agent_id)


def test_agent_list_reflects_profiles_and_chat_uses_conversation_agent(tmp_path: Path) -> None:
    db = tmp_path / 'db.sqlite'
    _write_multi_agent_db(db)
    context = build_context(str(db))
    engine = _FakeStreamEngine()
    transcript = SessionService(JsonlSessionStore(str(tmp_path / 'console_transcript.jsonl')))
    context = replace(context, engine=engine, transcript_service=transcript)
    app = create_app(str(db), app_context=context)
    client = TestClient(app)

    token = _login(client)
    headers = {'Authorization': f'Bearer {token}'}

    agents = client.get('/api/agent', headers=headers)
    assert agents.status_code == 200
    items = agents.json()['items']
    assert {item['_id'] for item in items} == {'default', 'claim'}

    created = client.post('/api/conversation', headers=headers, json={'agentId': 'claim'})
    assert created.status_code == 200
    conversation_id = created.json()['_id']

    stream = client.post(
        '/api/message/chat',
        headers=headers,
        data={'conversationId': conversation_id, 'text': 'hi claim'},
    )
    assert stream.status_code == 200
    assert engine.calls[-1] == ('hi claim', conversation_id, 'claim')


def test_conversation_history_survives_context_rebuild(tmp_path: Path) -> None:
    db = write_runtime_db(tmp_path / 'db.sqlite', project_root=tmp_path)

    first_context = build_context(str(db))
    first_context = replace(first_context, engine=_FakeStreamEngine())
    first_app = create_app(str(db), app_context=first_context)
    first_client = TestClient(first_app)
    token = _login(first_client)
    headers = {'Authorization': f'Bearer {token}'}

    created = first_client.post('/api/conversation', headers=headers, json={'agentId': 'default'})
    assert created.status_code == 200
    conversation_id = created.json()['_id']

    stream = first_client.post(
        '/api/message/chat',
        headers=headers,
        data={'conversationId': conversation_id, 'text': 'persist me'},
    )
    assert stream.status_code == 200

    rebuilt_context = build_context(str(db))
    rebuilt_app = create_app(str(db), app_context=rebuilt_context)
    rebuilt_client = TestClient(rebuilt_app)
    rebuilt_token = _login(rebuilt_client)
    rebuilt_headers = {'Authorization': f'Bearer {rebuilt_token}'}

    conversations = rebuilt_client.get('/api/conversation/agent/default', headers=rebuilt_headers)
    assert conversations.status_code == 200
    assert {item['_id'] for item in conversations.json()['items']} >= {conversation_id}

    messages = rebuilt_client.get(f'/api/message/conversation/{conversation_id}', headers=rebuilt_headers)
    assert messages.status_code == 200
    assert messages.json()['total'] >= 2


def test_transcript_bootstrap_restores_agent_ownership_without_conversation_metadata(tmp_path: Path) -> None:
    db = tmp_path / 'db.sqlite'
    _write_multi_agent_db(db)

    first_context = build_context(str(db))
    first_context = replace(first_context, engine=_FakeStreamEngine())
    first_app = create_app(str(db), app_context=first_context)
    first_client = TestClient(first_app)
    token = _login(first_client)
    headers = {'Authorization': f'Bearer {token}'}

    created = first_client.post('/api/conversation', headers=headers, json={'agentId': 'claim'})
    assert created.status_code == 200
    conversation_id = created.json()['_id']

    stream = first_client.post(
        '/api/message/chat',
        headers=headers,
        data={'conversationId': conversation_id, 'text': 'claim history'},
    )
    assert stream.status_code == 200

    metadata_file = tmp_path / 'data' / 'conversations.json'
    if metadata_file.exists():
        metadata_file.unlink()

    rebuilt_context = build_context(str(db))
    rebuilt_app = create_app(str(db), app_context=rebuilt_context)
    rebuilt_client = TestClient(rebuilt_app)
    rebuilt_token = _login(rebuilt_client)
    rebuilt_headers = {'Authorization': f'Bearer {rebuilt_token}'}

    claim_conversations = rebuilt_client.get('/api/conversation/agent/claim', headers=rebuilt_headers)
    assert claim_conversations.status_code == 200
    assert {item['_id'] for item in claim_conversations.json()['items']} >= {conversation_id}

    default_conversations = rebuilt_client.get('/api/conversation/agent/default', headers=rebuilt_headers)
    assert default_conversations.status_code == 200
    assert conversation_id not in {item['_id'] for item in default_conversations.json()['items']}
