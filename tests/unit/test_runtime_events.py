"""Unit tests for runtime event types and session/run API schemas."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from pydantic import TypeAdapter, ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.api.schemas.common import ErrorEnvelope
from csbot.api.schemas.run import RunRequest, RunSummary, RunEvent
from csbot.api.schemas.session import SessionSummary
from csbot.runtime.events import RUNTIME_EVENT_TYPE_VALUES, RuntimeEvent


def test_runtime_event_types_match_phase1_spec() -> None:
    assert RUNTIME_EVENT_TYPE_VALUES == frozenset(
        ("started", "planning", "delta", "tool_call", "tool_result", "done", "error")
    )


def test_runtime_event_discriminated_union_parses_delta() -> None:
    adapter = TypeAdapter(RuntimeEvent)
    ev = adapter.validate_python({"type": "delta", "delta": "你好", "run_id": "run_1"})
    assert ev.type == "delta"
    assert ev.delta == "你好"
    assert ev.run_id == "run_1"


@pytest.mark.parametrize(
    ("payload", "expected_type", "checks"),
    [
        (
            {"type": "started", "run_id": "r1", "session_id": "s1"},
            "started",
            lambda e: e.run_id == "r1" and e.session_id == "s1",
        ),
        (
            {"type": "planning", "run_id": "r1"},
            "planning",
            lambda e: e.run_id == "r1",
        ),
        (
            {"type": "planning"},
            "planning",
            lambda e: e.run_id is None and e.session_id is None,
        ),
        (
            {"type": "delta", "delta": "x"},
            "delta",
            lambda e: e.delta == "x",
        ),
        (
            {
                "type": "tool_call",
                "name": "read_file",
                "arguments": {"path": "/tmp/a"},
                "run_id": "r2",
            },
            "tool_call",
            lambda e: e.name == "read_file" and e.arguments == {"path": "/tmp/a"} and e.run_id == "r2",
        ),
        (
            {"type": "tool_result", "name": "read_file", "content": "ok"},
            "tool_result",
            lambda e: e.name == "read_file" and e.content == "ok",
        ),
        (
            {"type": "done", "reply": "final", "session_id": "s9"},
            "done",
            lambda e: e.reply == "final" and e.session_id == "s9",
        ),
        (
            {"type": "done"},
            "done",
            lambda e: e.reply is None,
        ),
        (
            {"type": "error", "message": "boom", "code": "E1", "run_id": "r3"},
            "error",
            lambda e: e.message == "boom" and e.code == "E1" and e.run_id == "r3",
        ),
    ],
)
def test_runtime_event_union_accepts_all_phase1_variants(
    payload: dict,
    expected_type: str,
    checks,
) -> None:
    adapter = TypeAdapter(RuntimeEvent)
    ev = adapter.validate_python(payload)
    assert ev.type == expected_type
    assert checks(ev)


@pytest.mark.parametrize(
    "bad_payload",
    [
        {"type": "not_a_real_event"},
        {"type": 123},
        {},
    ],
)
def test_runtime_event_union_rejects_unknown_or_missing_discriminator(bad_payload: dict) -> None:
    adapter = TypeAdapter(RuntimeEvent)
    with pytest.raises(ValidationError):
        adapter.validate_python(bad_payload)


@pytest.mark.parametrize(
    ("payload", "missing_field_hint"),
    [
        ({"type": "started"}, "run_id"),
        ({"type": "started", "session_id": "s"}, "run_id"),
        ({"type": "delta", "run_id": "r"}, "delta"),
        ({"type": "tool_call", "run_id": "r"}, "name"),
        ({"type": "tool_result", "content": "x"}, "name"),
        ({"type": "error", "code": "x"}, "message"),
    ],
)
def test_runtime_event_union_rejects_missing_required_fields(
    payload: dict,
    missing_field_hint: str,
) -> None:
    adapter = TypeAdapter(RuntimeEvent)
    with pytest.raises(ValidationError) as exc_info:
        adapter.validate_python(payload)
    err_text = str(exc_info.value)
    assert missing_field_hint in err_text


def test_run_request_matches_approved_spec_shape() -> None:
    payload = {
        "input": {"message": "帮我分析这段日志"},
        "agent": {"id": "general-assistant", "mode": "chat"},
        "model": {"provider": "litellm", "model": "claude-3-7-sonnet"},
        "session_id": "sess_xxx",
        "stream": True,
        "metadata": {"source": "web"},
    }
    req = RunRequest.model_validate(payload)
    assert req.input.message == "帮我分析这段日志"
    assert req.agent.id == "general-assistant"
    assert req.agent.mode == "chat"
    assert req.model.provider == "litellm"
    assert req.model.model == "claude-3-7-sonnet"
    assert req.session_id == "sess_xxx"
    assert req.stream is True
    assert req.metadata == {"source": "web"}


def test_session_and_run_summaries_and_error_envelope() -> None:
    sess = SessionSummary(session_id="sess_a", latest_run_id="run_b")
    assert sess.session_id == "sess_a"
    assert sess.latest_run_id == "run_b"

    run = RunSummary(run_id="run_b", session_id="sess_a", status="succeeded")
    assert run.status == "succeeded"

    err = ErrorEnvelope(
        code="validation_error",
        message="bad",
        run_id="run_b",
        session_id="sess_a",
        retryable=False,
    )
    assert err.code == "validation_error"

    # Transport RunEvent is the same discriminated union as runtime RuntimeEvent
    adapter = TypeAdapter(RunEvent)
    ev = adapter.validate_python({"type": "started", "run_id": "run_b", "session_id": "sess_a"})
    assert ev.type == "started"
