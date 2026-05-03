"""Unit tests for RuntimeService (event stream orchestration)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.config.settings import load_settings
from csbot.domain.errors import EngineError, ValidationError
from csbot.runtime.service import RuntimeService
from csbot.services.session_service import SessionService
from csbot.storage.jsonl_store import JsonlSessionStore
from csbot.uploads.service import AttachmentRow, InMemoryAttachmentRepository, UploadsService


def _write_minimal_conf(path: Path) -> None:
    root = path.parent
    skill_root = root / "skill-mgr"
    skill_root.mkdir(parents=True, exist_ok=True)
    sandbox_root = root / "sandbox"
    sandbox_root.mkdir(parents=True, exist_ok=True)
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    yaml_text = f"""
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
agent:
  skill_manager_root: {skill_root.as_posix()}
  skills_sources:
    - skills
  memory_files:
    - m.json
  thread_pool_workers: 2
  system_prompt: hi
sandbox:
  root_dir: {sandbox_root.as_posix()}
  virtual_mode: true
  execute_timeout_sec: 60
  max_output_chars: 10000
storage:
  session_jsonl_path: data/sessions.jsonl
  flush_mode: immediate
api:
  cors_allow_origins:
    - "*"
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
    path.write_text(yaml_text.strip() + "\n", encoding="utf-8")


class _FakeAgentRuntime:
    def __init__(
        self,
        *,
        deltas: list[str] | None = None,
        exc: BaseException | None = None,
    ) -> None:
        self._deltas = deltas or []
        self._exc = exc
        self.calls: list[tuple[str, str]] = []

    def iter_stream_deltas(self, user_input: str, thread_id: str) -> Iterator[str]:
        self.calls.append((user_input, thread_id))
        if self._exc:
            raise self._exc
        yield from self._deltas


@pytest.fixture
def settings(tmp_path: Path):
    load_settings.cache_clear()
    conf = tmp_path / "conf.yaml"
    _write_minimal_conf(conf)
    return load_settings(str(conf))


def test_runtime_service_emits_started_delta_done(settings, tmp_path: Path) -> None:
    runtime = _FakeAgentRuntime(deltas=["hel", "lo"])
    service = RuntimeService(settings, runtime)
    events = list(
        service.stream_run(
            message=" hi ",
            run_id="run_1",
            session_id="sess_1",
            thread_id="thread_a",
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
    list(
        service.stream_run(
            message=" hi ",
            run_id="run_1",
            session_id=None,
            thread_id="thread_x",
        )
    )
    lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    session_row = json.loads(lines[0])
    assert session_row["thread_id"] == "thread_x"
    assert isinstance(session_row["messages"], list)
    assert len(session_row["messages"]) == 2
    row0 = session_row["messages"][0]
    row1 = session_row["messages"][1]
    assert row0["role"] == "user" and row0["thread_id"] == "thread_x" and row0["content"] == "hi"
    assert row1["role"] == "assistant" and row1["thread_id"] == "thread_x" and row1["content"] == "ab"


def test_runtime_service_validation_raises_before_any_event(settings) -> None:
    service = RuntimeService(settings, _FakeAgentRuntime(deltas=["x"]))
    with pytest.raises(ValidationError):
        list(
            service.stream_run(
                message="   ",
                run_id="run_1",
                session_id="sess_1",
                thread_id="t1",
            )
        )


def test_runtime_service_emits_error_on_engine_failure(settings) -> None:
    service = RuntimeService(settings, _FakeAgentRuntime(exc=EngineError("agent failed")))
    events = list(
        service.stream_run(
            message="ok",
            run_id="run_2",
            session_id=None,
            thread_id="t2",
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
            thread_id="tx",
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
            thread_id="t0",
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
            thread_id="thread_ocr",
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
    final_input, thread_id = runtime.calls[0]
    assert thread_id == "thread_ocr"
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
            thread_id="thread_only_attachment",
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
    final_input, _ = runtime.calls[0]
    assert "standalone.md" in final_input
    assert "# 标题" in final_input
