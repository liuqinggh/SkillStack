from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from csbot.config_repository import SqliteRuntimeConfigRepository
from csbot.domain.errors import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = str((PROJECT_ROOT / "data" / "csbot.sqlite").resolve())


@dataclass(frozen=True)
class AppConfig:
    name: str
    version: str
    host: str
    port: int
    debug: bool


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    temperature: float
    timeout_sec: int
    max_tokens: int


@dataclass(frozen=True)
class AgentProfileConfig:
    skills_sources: list[str]
    memory_files: list[str]
    system_prompt: str


@dataclass(frozen=True)
class AgentConfig:
    skill_manager_root: str
    thread_pool_workers: int
    default_profile_id: str
    profiles: dict[str, AgentProfileConfig]

    def profile_ids(self) -> list[str]:
        return list(self.profiles.keys())

    def has_profile(self, profile_id: str | None) -> bool:
        if profile_id is None:
            return True
        return profile_id.strip() in self.profiles

    def resolve_profile(self, profile_id: str | None) -> AgentProfileConfig:
        pid = (profile_id or self.default_profile_id).strip() or self.default_profile_id
        profile = self.profiles.get(pid)
        if profile is None:
            raise ConfigError(f"Unknown agent profile id: {pid}")
        return profile

    def deployment_profile(self) -> AgentProfileConfig:
        """本进程唯一对外 Agent 的能力包（system prompt / skills / memory）。"""
        return self.resolve_profile(self.default_profile_id)


@dataclass(frozen=True)
class McpServerConfig:
    name: str
    transport: str
    command: str | None
    args: list[str]
    url: str | None
    env: dict[str, str]


@dataclass(frozen=True)
class McpConfig:
    enabled: bool
    startup_timeout_sec: int
    servers: list[McpServerConfig]


@dataclass(frozen=True)
class SandboxConfig:
    root_dir: str
    virtual_mode: bool
    execute_timeout_sec: int
    max_output_chars: int


@dataclass(frozen=True)
class StorageConfig:
    session_jsonl_path: str
    flush_mode: str


@dataclass(frozen=True)
class ApiConfig:
    cors_allow_origins: list[str]
    max_request_chars: int
    chat_timeout_sec: int


@dataclass(frozen=True)
class StreamConfig:
    sse_enabled: bool
    heartbeat_sec: int
    chunk_strategy: str


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    format: str
    file_path: str
    rotate_policy: str


@dataclass(frozen=True)
class AuthConfig:
    admin_email: str
    password_hash: str
    admin_name: str
    access_ttl_minutes: int


@dataclass(frozen=True)
class Settings:
    app: AppConfig
    llm: LlmConfig
    agent: AgentConfig
    mcp: McpConfig
    sandbox: SandboxConfig
    storage: StorageConfig
    api: ApiConfig
    stream: StreamConfig
    logging: LoggingConfig
    auth: AuthConfig
    project_root: Path
    bootstrap_db_path: Path


def _normalize_db_path(db_path: str) -> Path:
    path = Path(db_path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    return path


def _resolve_project_root(db_path: Path) -> Path:
    parent = db_path.resolve().parent
    if parent.name == "data":
        return parent.parent
    return parent


@lru_cache(maxsize=32)
def _load_settings_cached(resolved_db_path_str: str) -> Settings:
    db_path = Path(resolved_db_path_str)
    project_root = _resolve_project_root(db_path)
    repository = SqliteRuntimeConfigRepository(str(db_path), project_root=project_root)
    repository.ensure_ready()
    from csbot.config_repository.assembler import assemble_settings

    return assemble_settings(
        db_path=db_path,
        project_root=project_root,
        llm=repository.load_llm_config(),
        agent=repository.load_agent_config(),
        mcp=repository.load_mcp_config(),
        auth=repository.load_auth_config(),
    )


def load_settings(db_path: str = DEFAULT_DB_PATH) -> Settings:
    resolved = _normalize_db_path(db_path)
    return _load_settings_cached(str(resolved))


load_settings.cache_clear = _load_settings_cached.cache_clear  # type: ignore[method-assign]
