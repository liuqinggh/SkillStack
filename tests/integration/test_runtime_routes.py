"""Integration tests for runtime HTTP API (sessions, runs, SSE)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
import json
import sys

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot import create_app
from csbot.api.deps import AppContext, build_context, get_context
from csbot.config_repository.runtime_repository import RuntimeAgentConfigRecord, RuntimeAgentProfileRecord
from csbot.config_repository.seed import default_runtime_seed
from csbot.services.session_service import SessionService
from csbot.storage.jsonl_store import JsonlSessionStore
from csbot.uploads.service import InMemoryAttachmentRepository, UploadsService
from tests.support.sqlite_config import write_runtime_db


class _FakeStreamEngine:
    """Minimal engine for RuntimeService: yields fixed deltas without LLM."""

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
        yield "ok"


def _write_multi_agent_db(path: Path) -> None:
    seed = default_runtime_seed(path.parent)
    seed = replace(
        seed,
        llm=replace(seed.llm, model="gpt-4", base_url="http://127.0.0.1:4000/v1", api_key="sk-test", temperature=0.5, timeout_sec=30, max_tokens=1000),
        agent=RuntimeAgentConfigRecord(
            skill_manager_root=str(path.parent.resolve()),
            thread_pool_workers=2,
            default_profile_id="default",
            profiles=[
                RuntimeAgentProfileRecord(
                    agent_id="default",
                    name="Default Agent",
                    system_prompt="default prompt",
                    memory_files=["default-memory.json"],
                    skills_sources=["skills"],
                    enabled=True,
                    is_default=True,
                ),
                RuntimeAgentProfileRecord(
                    agent_id="claim",
                    name="Claim",
                    system_prompt="claim prompt",
                    memory_files=["claim-memory.json"],
                    skills_sources=["skills"],
                    enabled=True,
                    is_default=False,
                ),
            ],
        ),
    )
    write_runtime_db(path, project_root=path.parent, seed=seed)


def _parse_sse_lines(body: str) -> list[dict]:
    events: list[dict] = []
    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        for line in block.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


@pytest.fixture
def fake_context(tmp_path: Path) -> AppContext:
    get_context.cache_clear()
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path)
    base = build_context(str(db))
    transcript = SessionService(JsonlSessionStore(str(tmp_path / "integration_transcript.jsonl")))
    return replace(base, engine=_FakeStreamEngine(), transcript_service=transcript)


def test_legacy_chat_routes_are_not_registered(fake_context: AppContext) -> None:
    app = create_app(str(fake_context.settings.bootstrap_db_path), app_context=fake_context)
    client = TestClient(app)
    for path in ("/api/v1/chat", "/api/v1/chat/stream"):
        resp = client.post(
            path,
            json={"message": "hi", "thread_id": "t1"},
        )
        assert resp.status_code in {404, 405}, path


def test_create_and_get_session(fake_context: AppContext) -> None:
    app = create_app(str(fake_context.settings.bootstrap_db_path), app_context=fake_context)
    client = TestClient(app)
    created = client.post("/api/runtime/sessions")
    assert created.status_code == 200
    sid = created.json()["session_id"]
    assert sid
    got = client.get(f"/api/runtime/sessions/{sid}")
    assert got.status_code == 200
    assert got.json() == {"session_id": sid, "latest_run_id": None}


def test_get_unknown_session_returns_404(fake_context: AppContext) -> None:
    app = create_app(str(fake_context.settings.bootstrap_db_path), app_context=fake_context)
    client = TestClient(app)
    resp = client.get("/api/runtime/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_post_run_non_stream_updates_session_latest_run(fake_context: AppContext) -> None:
    app = create_app(str(fake_context.settings.bootstrap_db_path), app_context=fake_context)
    client = TestClient(app)
    sid = client.post("/api/runtime/sessions").json()["session_id"]
    body = {
        "input": {"message": "hello"},
        "agent": {"id": "default", "mode": "chat"},
        "model": {"provider": "litellm", "model": "gpt-4"},
        "session_id": sid,
        "stream": False,
        "metadata": None,
    }
    resp = client.post("/api/runtime/runs", json=body)
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["session_id"] == sid
    assert summary["status"] == "succeeded"
    run_id = summary["run_id"]
    assert run_id
    got = client.get(f"/api/runtime/sessions/{sid}")
    assert got.json()["latest_run_id"] == run_id


def test_post_run_stream_returns_runtime_sse_events(fake_context: AppContext) -> None:
    app = create_app(str(fake_context.settings.bootstrap_db_path), app_context=fake_context)
    client = TestClient(app)
    sid = client.post("/api/runtime/sessions").json()["session_id"]
    body = {
        "input": {"message": "hello"},
        "agent": {"id": "default", "mode": "chat"},
        "model": {"provider": "litellm", "model": "gpt-4"},
        "session_id": sid,
        "stream": True,
        "metadata": None,
    }
    with client.stream("POST", "/api/runtime/runs", json=body) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        raw = resp.read().decode("utf-8")
    events = _parse_sse_lines(raw)
    types = [e["type"] for e in events]
    assert types[0] == "started"
    assert "delta" in types
    assert types[-1] == "done"


def test_post_run_with_unknown_agent_returns_400(fake_context: AppContext) -> None:
    app = create_app(str(fake_context.settings.bootstrap_db_path), app_context=fake_context)
    client = TestClient(app)
    sid = client.post("/api/runtime/sessions").json()["session_id"]
    body = {
        "input": {"message": "hello", "attachments": []},
        "agent": {"id": "non-exist-agent", "mode": "chat"},
        "model": {"provider": "litellm", "model": "gpt-4"},
        "session_id": sid,
        "stream": False,
        "metadata": None,
    }
    resp = client.post("/api/runtime/runs", json=body)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "Unknown agent id" in detail
    assert "non-exist-agent" in detail
    assert "default" in detail


def test_post_run_accepts_non_default_configured_agent(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    _write_multi_agent_db(db)
    context = build_context(str(db))
    context = replace(context, engine=_FakeStreamEngine())
    app = create_app(str(db), app_context=context)
    client = TestClient(app)

    sid = client.post("/api/runtime/sessions").json()["session_id"]
    body = {
        "input": {"message": "hello"},
        "agent": {"id": "claim", "mode": "chat"},
        "model": {"provider": "litellm", "model": "gpt-4"},
        "session_id": sid,
        "stream": False,
        "metadata": None,
    }
    resp = client.post("/api/runtime/runs", json=body)
    assert resp.status_code == 200
    assert context.engine.calls[-1] == ("hello", sid, "claim")


def test_runtime_session_rejects_switching_agent_ids(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    _write_multi_agent_db(db)
    context = build_context(str(db))
    context = replace(context, engine=_FakeStreamEngine())
    app = create_app(str(db), app_context=context)
    client = TestClient(app)

    sid = client.post("/api/runtime/sessions").json()["session_id"]
    base_body = {
        "input": {"message": "hello"},
        "model": {"provider": "litellm", "model": "gpt-4"},
        "session_id": sid,
        "stream": False,
        "metadata": None,
    }
    first = client.post(
        "/api/runtime/runs",
        json={**base_body, "agent": {"id": "default", "mode": "chat"}},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/runtime/runs",
        json={**base_body, "agent": {"id": "claim", "mode": "chat"}},
    )
    assert second.status_code == 400
    assert "different agent" in second.json()["detail"]


def test_upload_endpoint_stores_attachment_and_run_can_reference_it(
    fake_context: AppContext,
    tmp_path: Path,
) -> None:
    sandbox = replace(fake_context.settings.sandbox, root_dir=tmp_path.as_posix())
    settings = replace(fake_context.settings, sandbox=sandbox)
    uploads_service = UploadsService(settings, InMemoryAttachmentRepository())
    context = replace(fake_context, settings=settings, uploads_service=uploads_service)
    app = create_app(str(context.settings.bootstrap_db_path), app_context=context)
    client = TestClient(app)

    sid = client.post("/api/runtime/sessions").json()["session_id"]
    upload = client.post(
        "/api/runtime/uploads",
        data={"session_id": sid, "ocr_mode": "auto"},
        files={"file": ("notes.txt", "hello from attachment", "text/plain")},
    )
    assert upload.status_code == 200
    payload = upload.json()
    assert payload["session_id"] == sid
    assert payload["kind"] == "text"
    assert payload["extraction_status"] == "ready"
    assert payload["extractor"] == "inline-text-preview"
    assert payload["attachment_id"]

    run = client.post(
        "/api/runtime/runs",
        json={
            "input": {
                "message": "请结合附件回答",
                "attachments": [payload["attachment_id"]],
            },
            "agent": {"id": "default", "mode": "chat"},
            "model": {"provider": "litellm", "model": "gpt-4"},
            "session_id": sid,
            "stream": False,
            "metadata": None,
        },
    )
    assert run.status_code == 200
    assert context.engine.calls
    final_input, thread_id, agent_id = context.engine.calls[-1]
    assert thread_id == sid
    assert agent_id == "default"
    assert "notes.txt" in final_input
    assert "hello from attachment" in final_input
    assert "请结合附件回答" in final_input


def test_upload_endpoint_rejects_unsupported_file_type(
    fake_context: AppContext,
    tmp_path: Path,
) -> None:
    sandbox = replace(fake_context.settings.sandbox, root_dir=tmp_path.as_posix())
    settings = replace(fake_context.settings, sandbox=sandbox)
    uploads_service = UploadsService(settings, InMemoryAttachmentRepository())
    context = replace(fake_context, settings=settings, uploads_service=uploads_service)
    app = create_app(str(context.settings.bootstrap_db_path), app_context=context)
    client = TestClient(app)

    sid = client.post("/api/runtime/sessions").json()["session_id"]
    upload = client.post(
        "/api/runtime/uploads",
        data={"session_id": sid, "ocr_mode": "auto"},
        files={"file": ("archive.zip", b"PK\x03\x04", "application/zip")},
    )
    assert upload.status_code == 400
    assert "不支持" in upload.json()["detail"]
