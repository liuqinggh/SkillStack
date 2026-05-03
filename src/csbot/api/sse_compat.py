from __future__ import annotations

import json

from csbot.runtime.events import RuntimeEventDelta, RuntimeEventDone, RuntimeEventError


def frontend_sse_line(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def from_runtime_event(evt: object) -> str | None:
    if isinstance(evt, RuntimeEventDelta):
        return frontend_sse_line({'type': 'response.output_text.delta', 'delta': evt.delta})
    if isinstance(evt, RuntimeEventDone):
        return frontend_sse_line({'type': 'response.output_text.delta', 'delta': ''})
    if isinstance(evt, RuntimeEventError):
        return frontend_sse_line({'type': 'response.error', 'delta': evt.message})
    return None
