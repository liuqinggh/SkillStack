from __future__ import annotations

import json
import threading
from collections import defaultdict
from pathlib import Path

from csbot.domain.models import SessionRecord


class JsonlSessionStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def append(self, record: SessionRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            grouped = self._read_grouped_unlocked()
            grouped[record.session_id].append(record)
            self._write_grouped_unlocked(grouped)

    def read_all(self) -> list[SessionRecord]:
        if not self.path.is_file():
            return []
        with self._lock:
            grouped = self._read_grouped_unlocked()
            rows = [row for records in grouped.values() for row in records]
            rows.sort(key=lambda r: r.ts)
            return rows

    def replace_all(self, records: list[SessionRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            grouped: dict[str, list[SessionRecord]] = defaultdict(list)
            for row in records:
                grouped[row.session_id].append(row)
            self._write_grouped_unlocked(grouped)

    @staticmethod
    def _record_payload(record: SessionRecord) -> dict:
        return {
            "message_id": record.message_id,
            "role": record.role,
            "content": record.content,
            "session_id": record.session_id,
            "ts": record.ts,
            "thinking": record.thinking,
            "files": record.files or [],
        }

    def _read_grouped_unlocked(self) -> dict[str, list[SessionRecord]]:
        grouped: dict[str, list[SessionRecord]] = defaultdict(list)
        if not self.path.is_file():
            return grouped
        with self.path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue

                # New format: one line per session_id, messages in payload["messages"].
                if isinstance(payload.get("messages"), list):
                    session_id = str(payload.get("session_id") or payload.get("thread_id") or "")
                    for msg in payload["messages"]:
                        if not isinstance(msg, dict):
                            continue
                        row_payload = dict(msg)
                        row_payload["session_id"] = str(
                            row_payload.get("session_id") or row_payload.get("thread_id") or session_id
                        )
                        row = SessionRecord.from_json(row_payload)
                        grouped[row.session_id].append(row)
                    continue

                # Backward compatibility: old format, one message per line.
                row = SessionRecord.from_json(payload)
                grouped[row.session_id].append(row)

        for rows in grouped.values():
            rows.sort(key=lambda r: r.ts)
        return grouped

    def _write_grouped_unlocked(self, grouped: dict[str, list[SessionRecord]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for session_id in sorted(grouped.keys()):
                rows = sorted(grouped[session_id], key=lambda r: r.ts)
                line = json.dumps(
                    {
                        "session_id": session_id,
                        "messages": [self._record_payload(r) for r in rows],
                    },
                    ensure_ascii=False,
                )
                f.write(line + "\n")
