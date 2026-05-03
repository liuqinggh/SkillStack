"""Input validation and small lifecycle helpers for agent runs."""

from __future__ import annotations

from csbot.config.settings import Settings
from csbot.domain.errors import ValidationError


def validate_run_message(settings: Settings, message: str, *, allow_empty: bool = False) -> str:
    text = (message or "").strip()
    if not text and not allow_empty:
        raise ValidationError("message 不能为空")
    if len(text) > settings.api.max_request_chars:
        raise ValidationError("message 过长")
    return text
