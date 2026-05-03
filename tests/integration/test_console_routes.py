"""Integration tests for Hermes-client compatibility routes."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
import sys
import textwrap

from fastapi.testclient import TestClient
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot import create_app
from csbot.api.deps import AppContext, build_context, get_context
from csbot.services.session_service import SessionService
from csbot.storage.jsonl_store import JsonlSessionStore


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


def _write_multi_agent_conf(path: Path) -> None:
    root = path.parent
    sandbox_root = root / "sandbox"
    sandbox_root.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""
            app:
              name: t
              version: 0.1.0
              host: 0.0.0.0
              port: 8000
              debug: false
            llm:
              provider: litellm
              model: gpt-4
              base_url: http://127.0.0.1:4000/v1
              api_key: sk-test
              temperature: 0.5
              timeout_sec: 30
              max_tokens: 1000
            agent:
              skill_manager_root: {root.as_posix()}
              thread_pool_workers: 2
              default_profile_id: default
              profiles:
                default:
                  skills_sources: [skills]
                  memory_files: [default-memory.json]
                  system_prompt: default prompt
                claim:
                  skills_sources: [skills]
                  memory_files: [claim-memory.json]
                  system_prompt: claim prompt
            sandbox:
              root_dir: {sandbox_root.as_posix()}
              virtual_mode: true
              execute_timeout_sec: 60
              max_output_chars: 10000
            storage:
              session_jsonl_path: data/sessions.jsonl
              flush_mode: immediate
            api:
              cors_allow_origins: ["*"]
              max_request_chars: 1000
            stream:
              sse_enabled: false
              heartbeat_sec: 15
              chunk_strategy: delta
            logging:
              level: INFO
              format: text
              file_path: ""
              rotate_policy: ""
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def fake_context(tmp_path: Path) -> AppContext:
    get_context.cache_clear()
    base = build_context(str(PROJECT_ROOT / 'conf.yaml'))
    transcript = SessionService(JsonlSessionStore(str(tmp_path / 'console_transcript.jsonl')))
    return replace(base, engine=_FakeStreamEngine(), transcript_service=transcript)


def _login(client: TestClient) -> str:
    resp = client.post('/api/auth/login', json={'email': 'admin@admin.com', 'password': '123456'})
    assert resp.status_code == 200
    return resp.json()['accessToken']


def test_console_routes_and_chat_stream(fake_context: AppContext) -> None:
    app = create_app(str(PROJECT_ROOT / 'conf.yaml'), app_context=fake_context)
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
    conf = tmp_path / 'conf.yaml'
    _write_multi_agent_conf(conf)
    context = build_context(str(conf))
    engine = _FakeStreamEngine()
    transcript = SessionService(JsonlSessionStore(str(tmp_path / 'console_transcript.jsonl')))
    context = replace(context, engine=engine, transcript_service=transcript)
    app = create_app(str(conf), app_context=context)
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
