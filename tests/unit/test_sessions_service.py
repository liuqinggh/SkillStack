"""Unit tests for runtime-oriented SessionsService + in-memory repository."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.api.deps import AppContext, build_context
from csbot.domain.errors import SessionNotFoundError
from csbot.services.session_service import SessionService
from csbot.sessions.repository import InMemorySessionRepository
from csbot.sessions.service import SessionsService
from csbot.config.settings import load_settings
from tests.support.sqlite_config import write_runtime_db


@pytest.fixture
def sessions_service() -> SessionsService:
    return SessionsService(InMemorySessionRepository())


def test_create_and_get_session_summary(sessions_service: SessionsService) -> None:
    sid = sessions_service.create_session()
    summary = sessions_service.get_summary(sid)
    assert summary is not None
    assert summary.session_id == sid
    assert summary.latest_run_id is None


def test_record_latest_run_updates_summary(sessions_service: SessionsService) -> None:
    sid = sessions_service.create_session()
    sessions_service.record_latest_run(sid, "run_abc")
    summary = sessions_service.get_summary(sid)
    assert summary is not None
    assert summary.latest_run_id == "run_abc"


def test_record_latest_run_unknown_session_raises(sessions_service: SessionsService) -> None:
    missing = "no-such-session"
    with pytest.raises(SessionNotFoundError) as excinfo:
        sessions_service.record_latest_run(missing, "run_x")
    assert excinfo.value.session_id == missing


def test_build_context_wires_sessions_service(tmp_path: Path) -> None:
    load_settings.cache_clear()
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path)
    ctx = build_context(str(db))
    assert isinstance(ctx, AppContext)
    assert isinstance(ctx.sessions_service, SessionsService)
    assert isinstance(ctx.transcript_service, SessionService)
    sid = ctx.sessions_service.create_session()
    ctx.sessions_service.record_latest_run(sid, "run_wired")
    summary = ctx.sessions_service.get_summary(sid)
    assert summary is not None
    assert summary.session_id == sid
    assert summary.latest_run_id == "run_wired"
