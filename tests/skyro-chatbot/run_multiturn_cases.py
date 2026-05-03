from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_AGENT_ID = "default"
DEFAULT_MODEL = "gemini-2.5-flash"


@dataclass
class CaseSpec:
    name: str
    turns_file: Path
    materials_dir: Path | None
    config: dict[str, Any]


@dataclass
class TurnResult:
    index: int
    run_id: str
    status: str
    prompt_preview: str


@dataclass
class CaseResult:
    case_name: str
    session_id: str
    stream: bool
    attachment_count: int
    latest_run_id: str | None
    turn_results: list[TurnResult]
    passed: bool
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multi-turn chatbot scenarios with optional attachments."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8888",
        help="Runtime service base url. Default: http://127.0.0.1:8888",
    )
    parser.add_argument(
        "--cases-root",
        default="tests/skyro-chatbot",
        help="Root directory containing test cases.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Use SSE stream mode for each turn.",
    )
    parser.add_argument(
        "--agent-id",
        default=DEFAULT_AGENT_ID,
        help=f"agent.id in request body. Default: {DEFAULT_AGENT_ID}",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"model.model in request body. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-request timeout seconds. Default: 120",
    )
    parser.add_argument(
        "--report-json",
        default="",
        help="Optional JSON report output path.",
    )
    parser.add_argument(
        "--report-csv",
        default="",
        help="Optional CSV report output path.",
    )
    return parser.parse_args()


def _looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return stripped.endswith(":") or stripped.endswith("：")


def parse_turns(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"Turn file is empty: {path}")

    lines = raw.splitlines()
    segments: list[str] = []
    heading: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal heading, buf
        content = "\n".join(x for x in buf if x.strip()).strip()
        if content:
            if heading:
                segments.append(f"{heading}\n{content}")
            else:
                segments.append(content)
        heading = None
        buf = []

    for line in lines:
        if _looks_like_heading(line):
            flush()
            heading = line.strip()
            continue
        if not line.strip() and not buf:
            continue
        buf.append(line)
    flush()

    if segments:
        return segments

    # Fallback: split by empty lines.
    fallback = [x.strip() for x in raw.split("\n\n") if x.strip()]
    if not fallback:
        raise ValueError(f"No turns parsed from {path}")
    return fallback


def discover_cases(cases_root: Path) -> list[CaseSpec]:
    candidates: list[CaseSpec] = []

    # Pattern A: tests/skyro-chatbot/cases/<case_name>/...
    cases_dir = cases_root / "cases"
    if cases_dir.is_dir():
        for case_dir in sorted(x for x in cases_dir.iterdir() if x.is_dir()):
            turns_file = case_dir / "user-turns.txt"
            if not turns_file.is_file():
                continue
            config_file = case_dir / "case.json"
            config = {}
            if config_file.is_file():
                config = json.loads(config_file.read_text(encoding="utf-8"))
            materials_dir = case_dir / "materials"
            candidates.append(
                CaseSpec(
                    name=case_dir.name,
                    turns_file=turns_file,
                    materials_dir=materials_dir if materials_dir.is_dir() else None,
                    config=config,
                )
            )

    # Pattern B: tests/skyro-chatbot/user-turns.txt (single case)
    root_turns = cases_root / "user-turns.txt"
    if root_turns.is_file():
        config_file = cases_root / "case.json"
        config = {}
        if config_file.is_file():
            config = json.loads(config_file.read_text(encoding="utf-8"))
        materials_dir = cases_root / "materials"
        candidates.append(
            CaseSpec(
                name="default",
                turns_file=root_turns,
                materials_dir=materials_dir if materials_dir.is_dir() else None,
                config=config,
            )
        )

    if not candidates:
        raise FileNotFoundError(
            f"No cases found in {cases_root}. Expected user-turns.txt under root or cases/<name>/."
        )
    return candidates


def create_session(base_url: str, timeout: float) -> str:
    resp = requests.post(f"{base_url}/api/runtime/sessions", timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    return payload["session_id"]


def upload_materials(
    base_url: str,
    session_id: str,
    materials_dir: Path | None,
    timeout: float,
) -> list[str]:
    if materials_dir is None:
        return []

    attachment_ids: list[str] = []
    files = sorted(x for x in materials_dir.iterdir() if x.is_file())
    for file_path in files:
        with file_path.open("rb") as f:
            resp = requests.post(
                f"{base_url}/api/runtime/uploads",
                data={"session_id": session_id, "ocr_mode": "auto"},
                files={"file": (file_path.name, f)},
                timeout=timeout,
            )
        resp.raise_for_status()
        payload = resp.json()
        attachment_ids.append(payload["attachment_id"])
    return attachment_ids


def parse_sse_events(raw: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


def run_one_turn(
    base_url: str,
    session_id: str,
    turn_text: str,
    attachment_ids: list[str],
    stream: bool,
    agent_id: str,
    model: str,
    timeout: float,
) -> tuple[str, str]:
    body = {
        "input": {"message": turn_text, "attachments": attachment_ids},
        "agent": {"id": agent_id, "mode": "chat"},
        "model": {"provider": "litellm", "model": model},
        "session_id": session_id,
        "stream": stream,
        "metadata": None,
    }

    if not stream:
        resp = requests.post(f"{base_url}/api/runtime/runs", json=body, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("run_id", ""), payload.get("status", "")

    with requests.post(
        f"{base_url}/api/runtime/runs",
        json=body,
        stream=True,
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()
        raw = resp.text

    events = parse_sse_events(raw)
    if not events:
        raise RuntimeError("SSE stream returned no events")

    run_id = str(events[0].get("run_id", ""))
    last_type = str(events[-1].get("type", ""))
    if last_type == "done":
        return run_id, "succeeded"
    if last_type == "error":
        return run_id, "failed"
    return run_id, "unknown"


def assert_case_expectations(case: CaseSpec, statuses: list[str]) -> None:
    expected = case.config.get("expected_final_status")
    if expected and statuses and statuses[-1] != expected:
        raise AssertionError(
            f"[{case.name}] expected final status {expected!r}, got {statuses[-1]!r}"
        )

    must_all_succeed = case.config.get("all_turns_must_succeed", True)
    if must_all_succeed and any(s != "succeeded" for s in statuses):
        raise AssertionError(f"[{case.name}] not all turns succeeded: {statuses}")


def run_case(
    case: CaseSpec,
    base_url: str,
    stream: bool,
    agent_id: str,
    model: str,
    timeout: float,
) -> CaseResult:
    turns = parse_turns(case.turns_file)
    session_id = create_session(base_url, timeout)
    attachment_ids = upload_materials(base_url, session_id, case.materials_dir, timeout)

    print(f"\n=== Case: {case.name} ===")
    print(f"session_id: {session_id}")
    print(f"turns: {len(turns)}, attachments: {len(attachment_ids)}, stream={stream}")

    statuses: list[str] = []
    turn_results: list[TurnResult] = []
    for idx, turn in enumerate(turns, start=1):
        run_id, status = run_one_turn(
            base_url=base_url,
            session_id=session_id,
            turn_text=turn,
            attachment_ids=attachment_ids,
            stream=stream,
            agent_id=agent_id,
            model=model,
            timeout=timeout,
        )
        statuses.append(status)
        preview = turn.replace("\n", " ")[:80]
        turn_results.append(
            TurnResult(
                index=idx,
                run_id=run_id,
                status=status,
                prompt_preview=preview,
            )
        )
        print(f"[turn {idx}] run_id={run_id} status={status} prompt={preview!r}")

    # Ensure latest_run_id exists and syncs at least once.
    sess_resp = requests.get(f"{base_url}/api/runtime/sessions/{session_id}", timeout=timeout)
    sess_resp.raise_for_status()
    latest_run = sess_resp.json().get("latest_run_id")
    print(f"latest_run_id: {latest_run}")

    assert_case_expectations(case, statuses)
    print(f"[{case.name}] PASS")
    return CaseResult(
        case_name=case.name,
        session_id=session_id,
        stream=stream,
        attachment_count=len(attachment_ids),
        latest_run_id=latest_run,
        turn_results=turn_results,
        passed=True,
    )


def write_json_report(path: Path, results: list[CaseResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(results),
        "failed_cases": sum(1 for r in results if not r.passed),
        "cases": [
            {
                "case_name": r.case_name,
                "session_id": r.session_id,
                "stream": r.stream,
                "attachment_count": r.attachment_count,
                "latest_run_id": r.latest_run_id,
                "passed": r.passed,
                "error": r.error,
                "turns": [
                    {
                        "index": t.index,
                        "run_id": t.run_id,
                        "status": t.status,
                        "prompt_preview": t.prompt_preview,
                    }
                    for t in r.turn_results
                ],
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv_report(path: Path, results: list[CaseResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "case_name",
                "session_id",
                "stream",
                "attachment_count",
                "turn_index",
                "run_id",
                "status",
                "latest_run_id",
                "case_passed",
                "error",
                "prompt_preview",
            ]
        )
        for r in results:
            if not r.turn_results:
                writer.writerow(
                    [
                        r.case_name,
                        r.session_id,
                        r.stream,
                        r.attachment_count,
                        "",
                        "",
                        "",
                        r.latest_run_id or "",
                        r.passed,
                        r.error or "",
                        "",
                    ]
                )
                continue
            for t in r.turn_results:
                writer.writerow(
                    [
                        r.case_name,
                        r.session_id,
                        r.stream,
                        r.attachment_count,
                        t.index,
                        t.run_id,
                        t.status,
                        r.latest_run_id or "",
                        r.passed,
                        r.error or "",
                        t.prompt_preview,
                    ]
                )


def main() -> None:
    args = parse_args()
    root = Path(args.cases_root).resolve()
    cases = discover_cases(root)
    print(f"Found {len(cases)} case(s) under {root}")

    failed = 0
    results: list[CaseResult] = []
    for case in cases:
        try:
            result = run_case(
                case=case,
                base_url=args.base_url.rstrip("/"),
                stream=args.stream,
                agent_id=args.agent_id,
                model=args.model,
                timeout=args.timeout,
            )
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[{case.name}] FAIL: {exc}")
            results.append(
                CaseResult(
                    case_name=case.name,
                    session_id="",
                    stream=args.stream,
                    attachment_count=0,
                    latest_run_id=None,
                    turn_results=[],
                    passed=False,
                    error=str(exc),
                )
            )

    if args.report_json:
        json_path = Path(args.report_json)
        write_json_report(json_path, results)
        print(f"JSON report written: {json_path}")
    if args.report_csv:
        csv_path = Path(args.report_csv)
        write_csv_report(csv_path, results)
        print(f"CSV report written: {csv_path}")

    if failed:
        raise SystemExit(f"{failed} case(s) failed")
    print("\nAll cases passed.")


if __name__ == "__main__":
    main()
