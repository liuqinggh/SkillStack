from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).with_name("run_multiturn_cases.py")
SPEC = importlib.util.spec_from_file_location("run_multiturn_cases", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


CaseSpec = MODULE.CaseSpec
CaseResult = MODULE.CaseResult
TurnResult = MODULE.TurnResult
assert_case_expectations = MODULE.assert_case_expectations
discover_cases = MODULE.discover_cases
parse_sse_events = MODULE.parse_sse_events
parse_turns = MODULE.parse_turns
write_csv_report = MODULE.write_csv_report
write_json_report = MODULE.write_json_report


def test_parse_turns_with_headings(tmp_path: Path) -> None:
    turns_file = tmp_path / "user-turns.txt"
    turns_file.write_text(
        "chronology:\n"
        "phone dropped and cracked\n\n"
        "personal info:\n"
        "John Doe, 0917xxxxxxx\n",
        encoding="utf-8",
    )

    turns = parse_turns(turns_file)
    assert len(turns) == 2
    assert turns[0].startswith("chronology:")
    assert "phone dropped" in turns[0]
    assert turns[1].startswith("personal info:")


def test_parse_turns_without_headings_is_single_turn(tmp_path: Path) -> None:
    turns_file = tmp_path / "user-turns.txt"
    turns_file.write_text(
        "first question\n\nsecond question\n\nthird question\n",
        encoding="utf-8",
    )

    turns = parse_turns(turns_file)
    assert len(turns) == 1
    assert "first question" in turns[0]
    assert "second question" in turns[0]
    assert "third question" in turns[0]


def test_parse_sse_events() -> None:
    raw = (
        'data: {"type":"started","run_id":"r1"}\n\n'
        'data: {"type":"delta","delta":"ok"}\n'
        'data: {"type":"done","run_id":"r1"}\n\n'
    )
    events = parse_sse_events(raw)
    assert events[0]["type"] == "started"
    assert events[1]["type"] == "delta"
    assert events[2]["type"] == "done"


def test_assert_case_expectations_failure() -> None:
    case = CaseSpec(
        name="x",
        turns_file=Path("user-turns.txt"),
        materials_dir=None,
        config={"all_turns_must_succeed": True},
    )
    with pytest.raises(AssertionError):
        assert_case_expectations(case, ["succeeded", "failed"])


def test_discover_cases_supports_root_and_nested(tmp_path: Path) -> None:
    root_turns = tmp_path / "user-turns.txt"
    root_turns.write_text("hi", encoding="utf-8")

    nested_case_dir = tmp_path / "cases" / "case-a"
    nested_case_dir.mkdir(parents=True)
    (nested_case_dir / "user-turns.txt").write_text("hello", encoding="utf-8")
    (nested_case_dir / "case.json").write_text(
        json.dumps({"all_turns_must_succeed": True}),
        encoding="utf-8",
    )

    cases = discover_cases(tmp_path)
    names = sorted(x.name for x in cases)
    assert names == ["case-a", "default"]


def test_write_json_report(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    results = [
        CaseResult(
            case_name="case-a",
            session_id="sess-1",
            stream=True,
            attachment_count=1,
            latest_run_id="run-2",
            turn_results=[
                TurnResult(index=1, run_id="run-1", status="succeeded", prompt_preview="hello"),
                TurnResult(index=2, run_id="run-2", status="succeeded", prompt_preview="world"),
            ],
            passed=True,
            error=None,
        )
    ]

    write_json_report(report_path, results)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["total_cases"] == 1
    assert payload["failed_cases"] == 0
    assert payload["cases"][0]["case_name"] == "case-a"
    assert len(payload["cases"][0]["turns"]) == 2


def test_write_csv_report(tmp_path: Path) -> None:
    report_path = tmp_path / "report.csv"
    results = [
        CaseResult(
            case_name="case-b",
            session_id="sess-2",
            stream=False,
            attachment_count=0,
            latest_run_id="run-3",
            turn_results=[
                TurnResult(index=1, run_id="run-3", status="succeeded", prompt_preview="foo")
            ],
            passed=True,
            error=None,
        )
    ]

    write_csv_report(report_path, results)
    content = report_path.read_text(encoding="utf-8")
    assert "case_name,session_id,stream" in content
    assert "case-b,sess-2,False,0,1,run-3,succeeded,run-3,True" in content
