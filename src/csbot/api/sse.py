"""Server-Sent Events formatting for runtime streams."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def format_sse_event(payload: dict[str, Any] | BaseModel) -> str:
    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json", exclude_none=True)
    else:
        data = payload
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
