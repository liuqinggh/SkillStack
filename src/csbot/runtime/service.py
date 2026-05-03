"""Orchestrates a single run into normalized runtime events."""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from typing import Protocol

from csbot.config.settings import Settings
from csbot.domain.errors import DemoCsBotError, EngineError
from csbot.runtime.attachments import build_run_input_with_attachments
from csbot.runtime.events import (
    RuntimeEvent,
    RuntimeEventDelta,
    RuntimeEventDone,
    RuntimeEventError,
    RuntimeEventStarted,
)
from csbot.runtime.lifecycle import validate_run_message
from csbot.services.session_service import SessionService
from csbot.uploads.service import AttachmentRow, UploadsService


class SupportsAgentStream(Protocol):
    def iter_stream_deltas(
        self,
        user_input: str,
        session_id: str,
        *,
        agent_id: str | None = None,
    ) -> Iterator[str]:
        ...


class RuntimeService:
    def __init__(
        self,
        settings: Settings,
        agent_runtime: SupportsAgentStream,
        uploads_service: UploadsService | None = None,
        *,
        transcript_service: SessionService | None = None,
    ) -> None:
        self._settings = settings
        self._runtime = agent_runtime
        self._uploads_service = uploads_service
        self._transcript = transcript_service

    @staticmethod
    def _supports_agent_id_kwarg(method: object) -> bool:
        try:
            signature = inspect.signature(method)
        except (TypeError, ValueError):
            return False
        if "agent_id" in signature.parameters:
            return True
        return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())

    def stream_run(
        self,
        *,
        message: str,
        attachments: list[AttachmentRow] | None = None,
        run_id: str,
        session_id: str | None,
        session_stream_id: str,
        agent_id: str | None = None,
    ) -> Iterator[RuntimeEvent]:
        attachment_rows = attachments or []
        text = validate_run_message(self._settings, message, allow_empty=bool(attachment_rows))
        if attachment_rows:
            if self._uploads_service is None:
                raise RuntimeError("uploads_service is required when attachments are provided")
            text = build_run_input_with_attachments(
                message=text,
                attachments=attachment_rows,
                uploads_service=self._uploads_service,
            )

        transcript = self._transcript
        user_logged = False
        assistant_logged = False

        def log_user() -> None:
            nonlocal user_logged
            if transcript is not None and not user_logged:
                transcript.append_turn("user", text, session_id=session_stream_id)
                user_logged = True

        def log_assistant(body: str) -> None:
            nonlocal assistant_logged
            if transcript is not None and user_logged and not assistant_logged:
                transcript.append_turn("assistant", body, session_id=session_stream_id)
                assistant_logged = True

        log_user()
        yield RuntimeEventStarted(run_id=run_id, session_id=session_id)
        full_reply = ""
        try:
            stream_fn = self._runtime.iter_stream_deltas
            if agent_id is not None and self._supports_agent_id_kwarg(stream_fn):
                stream_iter = stream_fn(text, session_stream_id, agent_id=agent_id)
            else:
                stream_iter = stream_fn(text, session_stream_id)
            for delta in stream_iter:
                if not delta:
                    continue
                full_reply += delta
                yield RuntimeEventDelta(
                    delta=delta,
                    run_id=run_id,
                    session_id=session_id,
                )
            reply = full_reply or "(无回复)"
            yield RuntimeEventDone(reply=reply, run_id=run_id, session_id=session_id)
            log_assistant(reply)
        except EngineError as e:
            yield RuntimeEventError(
                message=str(e),
                code="engine_error",
                run_id=run_id,
                session_id=session_id,
            )
            log_assistant(f"[engine_error] {e}")
        except DemoCsBotError:
            raise
        except Exception as e:
            yield RuntimeEventError(
                message=str(e),
                code="unexpected_error",
                run_id=run_id,
                session_id=session_id,
            )
            log_assistant(f"[unexpected_error] {e}")
