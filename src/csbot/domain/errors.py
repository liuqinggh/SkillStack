class DemoCsBotError(Exception):
    """Base exception for demo-csbot."""


class ConfigError(DemoCsBotError):
    """Configuration validation or loading error."""


class ValidationError(DemoCsBotError):
    """Invalid user request."""


class EngineError(DemoCsBotError):
    """LLM/agent runtime error."""


class StorageError(DemoCsBotError):
    """Session storage error."""


class SessionNotFoundError(DemoCsBotError):
    """Runtime session id is unknown (distinct from request field validation)."""

    def __init__(self, session_id: str, message: str | None = None) -> None:
        self.session_id = session_id
        super().__init__(message or f"Session not found: {session_id}")
