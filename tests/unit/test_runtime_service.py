"""Unit tests for RuntimeService (event stream orchestration)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.config.settings import load_settings
from csbot.config_repository.seed import default_runtime_seed
from csbot.domain.errors import EngineError, ValidationError
from csbot.runtime.service import RuntimeService
from csbot.services.session_service import SessionService
from csbot.storage.jsonl_store import JsonlSessionStore
from csbot.uploads.service import AttachmentRow, InMemoryAttachmentRepository, UploadsService
from tests.support.sqlite_config import write_runtime_db


class _FakeAgentRuntime:
    def __init__(
        self,
        *,
        deltas: list[str] | None = None,
        exc: BaseException | None = None,
    ) -> None:
        self._deltas = deltas or []
        self._exc = exc
        self.calls: list[tuple[str, str, str | None]] = []

    def iter_stream_deltas(
        self,
        user_input: str,
        thread_id: str,
        *,
        agent_id: str | None = None,
    ) -> Iterator[str]:
        self.calls.append((user_input, thread_id, agent_id))
        if self._exc:
            raise self._exc
        yield from self._deltas


@pytest.fixture
def settings(tmp_path: Path):
    load_settings.cache_clear()
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path, seed=default_runtime_seed(tmp_path))
    return load_settings(str(db))


def test_runtime_service_emits_started_delta_done(settings, tmp_path: Path) -> None:
    runtime = _FakeAgentRuntime(deltas=["hel", "lo"])
    service = RuntimeService(settings, runtime)
    sid = "11111111-1111-4111-8111-111111111111"
    events = list(
        service.stream_run(
            message=" hi ",
            run_id="run_1",
            session_id="sess_1",
            session_stream_id=sid,
        )
    )
    assert [e.type for e in events] == ["started", "delta", "delta", "done"]
    assert events[0].run_id == "run_1" and events[0].session_id == "sess_1"
    assert events[1].delta == "hel" and events[2].delta == "lo"
    assert events[3].reply == "hello"


def test_runtime_service_appends_transcript_after_successful_turn(settings, tmp_path: Path) -> None:
    jsonl = tmp_path / "tr.jsonl"
    transcript = SessionService(JsonlSessionStore(str(jsonl)))
    service = RuntimeService(settings, _FakeAgentRuntime(deltas=["a", "b"]), transcript_service=transcript)
    sid = "22222222-2222-4222-8222-222222222222"
    list(
        service.stream_run(
            message=" hi ",
            run_id="run_1",
            session_id=None,
            session_stream_id=sid,
        )
    )
    lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    session_row = json.loads(lines[0])
    assert session_row["session_id"] == sid
    assert isinstance(session_row["messages"], list)
    assert len(session_row["messages"]) == 2
    row0 = session_row["messages"][0]
    row1 = session_row["messages"][1]
    assert row0["role"] == "user" and row0["session_id"] == sid and row0["content"] == "hi"
    assert row1["role"] == "assistant" and row1["session_id"] == sid and row1["content"] == "ab"


def test_runtime_service_validation_raises_before_any_event(settings) -> None:
    service = RuntimeService(settings, _FakeAgentRuntime(deltas=["x"]))
    with pytest.raises(ValidationError):
        list(
            service.stream_run(
                message="   ",
                run_id="run_1",
                session_id="sess_1",
                session_stream_id="33333333-3333-4333-8333-333333333333",
            )
        )


def test_runtime_service_emits_error_on_engine_failure(settings) -> None:
    service = RuntimeService(settings, _FakeAgentRuntime(exc=EngineError("agent failed")))
    events = list(
        service.stream_run(
            message="ok",
            run_id="run_2",
            session_id=None,
            session_stream_id="44444444-4444-4444-8444-444444444444",
        )
    )
    assert [e.type for e in events] == ["started", "error"]
    assert events[1].type == "error"
    assert "agent failed" in events[1].message
    assert events[1].run_id == "run_2"
    assert events[1].code == "engine_error"


def test_runtime_service_emits_error_on_unexpected_exception(settings) -> None:
    service = RuntimeService(settings, _FakeAgentRuntime(exc=RuntimeError("boom")))
    events = list(
        service.stream_run(
            message="ok",
            run_id="run_x",
            session_id="sx",
            session_stream_id="55555555-5555-4555-8555-555555555555",
        )
    )
    assert [e.type for e in events] == ["started", "error"]
    assert "boom" in events[1].message
    assert events[1].code == "unexpected_error"


def test_runtime_service_done_with_empty_deltas_uses_placeholder_reply(settings) -> None:
    service = RuntimeService(settings, _FakeAgentRuntime(deltas=[]))
    events = list(
        service.stream_run(
            message="x",
            run_id="r0",
            session_id="s0",
            session_stream_id="66666666-6666-4666-8666-666666666666",
        )
    )
    assert [e.type for e in events] == ["started", "done"]
    assert events[1].reply == "(无回复)"


def test_runtime_service_builds_attachment_context_for_text_and_ocr_files(settings, tmp_path: Path) -> None:
    text_file = tmp_path / "notes.txt"
    text_file.write_text("第一行\n第二行", encoding="utf-8")
    pdf_file = tmp_path / "evidence.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake")

    runtime = _FakeAgentRuntime(deltas=["ok"])
    uploads_service = UploadsService(settings, InMemoryAttachmentRepository())
    service = RuntimeService(settings, runtime, uploads_service=uploads_service)

    events = list(
        service.stream_run(
            message="请先看附件再总结",
            run_id="run_attachment",
            session_id="sess_ocr",
            session_stream_id="77777777-7777-4777-8777-777777777777",
            attachments=[
                AttachmentRow(
                    attachment_id="att_text",
                    session_id="sess_ocr",
                    filename="notes.txt",
                    media_type="text/plain",
                    stored_path=str(text_file),
                    size_bytes=text_file.stat().st_size,
                    kind="text",
                    ocr_mode="auto",
                ),
                AttachmentRow(
                    attachment_id="att_pdf",
                    session_id="sess_ocr",
                    filename="evidence.pdf",
                    media_type="application/pdf",
                    stored_path=str(pdf_file),
                    size_bytes=pdf_file.stat().st_size,
                    kind="ocr",
                    ocr_mode="auto",
                ),
            ],
        )
    )

    assert [e.type for e in events] == ["started", "delta", "done"]
    assert runtime.calls
    final_input, session_id, agent_id = runtime.calls[0]
    assert session_id == "77777777-7777-4777-8777-777777777777"
    assert agent_id is None
    assert "notes.txt" in final_input
    assert "第一行" in final_input
    assert "系统已在上传阶段完成内容提取" in final_input
    assert "提取状态" in final_input
    assert str(pdf_file) in final_input
    assert "请先看附件再总结" in final_input


def test_runtime_service_accepts_attachment_only_run(settings, tmp_path: Path) -> None:
    text_file = tmp_path / "standalone.md"
    text_file.write_text("# 标题", encoding="utf-8")

    runtime = _FakeAgentRuntime(deltas=["ok"])
    uploads_service = UploadsService(settings, InMemoryAttachmentRepository())
    service = RuntimeService(settings, runtime, uploads_service=uploads_service)

    events = list(
        service.stream_run(
            message="   ",
            run_id="run_only_attachment",
            session_id="sess_only_attachment",
            session_stream_id="88888888-8888-4888-8888-888888888888",
            attachments=[
                AttachmentRow(
                    attachment_id="att_only",
                    session_id="sess_only_attachment",
                    filename="standalone.md",
                    media_type="text/markdown",
                    stored_path=str(text_file),
                    size_bytes=text_file.stat().st_size,
                    kind="text",
                    ocr_mode="auto",
                )
            ],
        )
    )

    assert [e.type for e in events] == ["started", "delta", "done"]
    assert runtime.calls
    final_input, _, agent_id = runtime.calls[0]
    assert agent_id is None
    assert "standalone.md" in final_input
    assert "# 标题" in final_input


def test_runtime_service_passes_agent_id_when_supported(settings) -> None:
    runtime = _FakeAgentRuntime(deltas=["ok"])
    service = RuntimeService(settings, runtime)

    list(
        service.stream_run(
            message="hello",
            run_id="run_agent",
            session_id="sess_agent",
            session_stream_id="99999999-9999-4999-8999-999999999999",
            agent_id="claim",
        )
    )

    assert runtime.calls[-1] == (
        "hello",
        "99999999-9999-4999-8999-999999999999",
        "claim",
    )
