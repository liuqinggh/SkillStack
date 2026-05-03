from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from csbot.domain.errors import ConfigError


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
    project_root: Path
    conf_path: Path


def _required(data: dict[str, Any], key: str, parent: str) -> Any:
    if key not in data:
        raise ConfigError(f"Missing required config key: {parent}.{key}")
    return data[key]


def _as_list(value: Any, key: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v.strip() for v in value):
        raise ConfigError(f"Config key '{key}' must be a non-empty string list")
    return [v.strip() for v in value]


def _as_str_list(value: Any, key: str) -> list[str]:
    if not isinstance(value, list):
        raise ConfigError(f"Config key '{key}' must be a string list")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"Config key '{key}' must be a string list")
        out.append(item)
    return out


def _as_int(value: Any, key: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise ConfigError(f"Config key '{key}' must be an integer (got {value!r})") from e


def _as_float(value: Any, key: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise ConfigError(f"Config key '{key}' must be a number (got {value!r})") from e


def _as_str_dict(value: Any, key: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"Config key '{key}' must be a string map")
    out: dict[str, str] = {}
    for k, v in value.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ConfigError(f"Config key '{key}' must be a string map")
        out[k] = v
    return out


def _normalize_conf_path(conf_path: str) -> Path:
    """Resolve config path to an absolute path so cache keys match real files (cwd-safe)."""
    path = Path(conf_path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    return path


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError("Config root must be a mapping")
    return data


def _resolve_project_root(conf_path: Path) -> Path:
    return conf_path.resolve().parent


def _build_settings(data: dict[str, Any], conf_path: Path) -> Settings:
    root = _resolve_project_root(conf_path)

    app_raw = _required(data, "app", "root")
    llm_raw = _required(data, "llm", "root")
    agent_raw = _required(data, "agent", "root")
    mcp_raw = data.get("mcp", {})
    sandbox_raw = _required(data, "sandbox", "root")
    storage_raw = _required(data, "storage", "root")
    api_raw = _required(data, "api", "root")
    stream_raw = _required(data, "stream", "root")
    logging_raw = _required(data, "logging", "root")

    if not all(isinstance(x, dict) for x in [app_raw, llm_raw, agent_raw, sandbox_raw, storage_raw, api_raw, stream_raw, logging_raw]):
        raise ConfigError("All top-level config sections must be mappings")
    if not isinstance(mcp_raw, dict):
        raise ConfigError("Config section 'mcp' must be a mapping when present")

    app = AppConfig(
        name=str(_required(app_raw, "name", "app")),
        version=str(_required(app_raw, "version", "app")),
        host=str(_required(app_raw, "host", "app")),
        port=_as_int(_required(app_raw, "port", "app"), "app.port"),
        debug=bool(_required(app_raw, "debug", "app")),
    )

    llm = LlmConfig(
        provider=str(_required(llm_raw, "provider", "llm")),
        model=str(_required(llm_raw, "model", "llm")),
        base_url=str(_required(llm_raw, "base_url", "llm")),
        api_key=str(_required(llm_raw, "api_key", "llm")),
        temperature=_as_float(_required(llm_raw, "temperature", "llm"), "llm.temperature"),
        timeout_sec=_as_int(_required(llm_raw, "timeout_sec", "llm"), "llm.timeout_sec"),
        max_tokens=_as_int(llm_raw.get("max_tokens", 8192), "llm.max_tokens"),
    )

    profiles_raw = agent_raw.get("profiles")
    profiles: dict[str, AgentProfileConfig] = {}
    if isinstance(profiles_raw, dict) and profiles_raw:
        for pid, profile_raw in profiles_raw.items():
            if not isinstance(profile_raw, dict):
                raise ConfigError(f"agent.profiles.{pid} must be a mapping")
            profile_id = str(pid).strip()
            if not profile_id:
                raise ConfigError("agent.profiles contains an empty profile id")
            profiles[profile_id] = AgentProfileConfig(
                skills_sources=_as_list(
                    _required(profile_raw, "skills_sources", f"agent.profiles.{profile_id}"),
                    f"agent.profiles.{profile_id}.skills_sources",
                ),
                memory_files=_as_list(
                    _required(profile_raw, "memory_files", f"agent.profiles.{profile_id}"),
                    f"agent.profiles.{profile_id}.memory_files",
                ),
                system_prompt=str(_required(profile_raw, "system_prompt", f"agent.profiles.{profile_id}")),
            )
    else:
        profiles["default"] = AgentProfileConfig(
            skills_sources=_as_list(_required(agent_raw, "skills_sources", "agent"), "agent.skills_sources"),
            memory_files=_as_list(_required(agent_raw, "memory_files", "agent"), "agent.memory_files"),
            system_prompt=str(_required(agent_raw, "system_prompt", "agent")),
        )

    default_profile_id = str(agent_raw.get("default_profile_id", "default")).strip() or "default"
    if default_profile_id not in profiles:
        raise ConfigError(f"agent.default_profile_id '{default_profile_id}' not found in agent.profiles")

    agent = AgentConfig(
        skill_manager_root=str(Path(str(_required(agent_raw, "skill_manager_root", "agent"))).expanduser().resolve()),
        thread_pool_workers=_as_int(_required(agent_raw, "thread_pool_workers", "agent"), "agent.thread_pool_workers"),
        default_profile_id=default_profile_id,
        profiles=profiles,
    )

    mcp_servers: list[McpServerConfig] = []
    servers_raw = mcp_raw.get("servers", [])
    if not isinstance(servers_raw, list):
        raise ConfigError("mcp.servers must be a list")
    for idx, server_raw in enumerate(servers_raw):
        if not isinstance(server_raw, dict):
            raise ConfigError(f"mcp.servers[{idx}] must be a mapping")
        name = str(_required(server_raw, "name", f"mcp.servers[{idx}]")).strip()
        if not name:
            raise ConfigError(f"mcp.servers[{idx}].name must be non-empty")
        transport = str(server_raw.get("transport", "stdio")).strip() or "stdio"
        if transport not in {"stdio", "streamable_http", "sse"}:
            raise ConfigError(f"mcp.servers[{idx}].transport must be one of stdio/streamable_http/sse")
        command: str | None = None
        url: str | None = None
        if transport == "stdio":
            command = str(_required(server_raw, "command", f"mcp.servers[{idx}]")).strip()
            if not command:
                raise ConfigError(f"mcp.servers[{idx}].command must be non-empty when transport=stdio")
        else:
            url = str(_required(server_raw, "url", f"mcp.servers[{idx}]")).strip()
            if not url:
                raise ConfigError(f"mcp.servers[{idx}].url must be non-empty when transport={transport}")
        args = _as_str_list(server_raw.get("args", []), f"mcp.servers[{idx}].args")
        env = _as_str_dict(server_raw.get("env", {}), f"mcp.servers[{idx}].env")
        mcp_servers.append(
            McpServerConfig(
                name=name,
                transport=transport,
                command=command,
                args=args,
                url=url,
                env=env,
            )
        )
    mcp = McpConfig(
        enabled=bool(mcp_raw.get("enabled", False)),
        startup_timeout_sec=_as_int(mcp_raw.get("startup_timeout_sec", 20), "mcp.startup_timeout_sec"),
        servers=mcp_servers,
    )

    sandbox = SandboxConfig(
        root_dir=str(Path(str(_required(sandbox_raw, "root_dir", "sandbox"))).expanduser().resolve()),
        virtual_mode=bool(_required(sandbox_raw, "virtual_mode", "sandbox")),
        execute_timeout_sec=_as_int(_required(sandbox_raw, "execute_timeout_sec", "sandbox"), "sandbox.execute_timeout_sec"),
        max_output_chars=_as_int(_required(sandbox_raw, "max_output_chars", "sandbox"), "sandbox.max_output_chars"),
    )

    session_jsonl = Path(str(_required(storage_raw, "session_jsonl_path", "storage")))
    if not session_jsonl.is_absolute():
        session_jsonl = (root / session_jsonl).resolve()

    storage = StorageConfig(
        session_jsonl_path=str(session_jsonl),
        flush_mode=str(_required(storage_raw, "flush_mode", "storage")),
    )

    api = ApiConfig(
        cors_allow_origins=_as_list(_required(api_raw, "cors_allow_origins", "api"), "api.cors_allow_origins"),
        max_request_chars=_as_int(_required(api_raw, "max_request_chars", "api"), "api.max_request_chars"),
        chat_timeout_sec=_as_int(api_raw.get("chat_timeout_sec", 120), "api.chat_timeout_sec"),
    )

    stream = StreamConfig(
        sse_enabled=bool(_required(stream_raw, "sse_enabled", "stream")),
        heartbeat_sec=_as_int(_required(stream_raw, "heartbeat_sec", "stream"), "stream.heartbeat_sec"),
        chunk_strategy=str(_required(stream_raw, "chunk_strategy", "stream")),
    )

    logging_cfg = LoggingConfig(
        level=str(_required(logging_raw, "level", "logging")),
        format=str(_required(logging_raw, "format", "logging")),
        file_path=str(_required(logging_raw, "file_path", "logging")),
        rotate_policy=str(_required(logging_raw, "rotate_policy", "logging")),
    )

    if app.port <= 0 or app.port > 65535:
        raise ConfigError("app.port must be in range 1..65535")
    if not (0.0 <= llm.temperature <= 2.0):
        raise ConfigError("llm.temperature must be between 0 and 2")
    if llm.provider != "litellm":
        raise ConfigError(
            f'llm.provider must be "litellm" for runtime phase 1 (got {llm.provider!r})'
        )
    if llm.timeout_sec < 1:
        raise ConfigError("llm.timeout_sec must be >= 1")
    if llm.max_tokens < 1:
        raise ConfigError("llm.max_tokens must be >= 1")
    if agent.thread_pool_workers < 1:
        raise ConfigError("agent.thread_pool_workers must be >= 1")
    if mcp.startup_timeout_sec < 1:
        raise ConfigError("mcp.startup_timeout_sec must be >= 1")
    if mcp.enabled and not mcp.servers:
        raise ConfigError("mcp.enabled is true but mcp.servers is empty")
    if sandbox.execute_timeout_sec < 1:
        raise ConfigError("sandbox.execute_timeout_sec must be >= 1")
    if sandbox.max_output_chars < 100:
        raise ConfigError("sandbox.max_output_chars must be >= 100")

    return Settings(
        app=app,
        llm=llm,
        agent=agent,
        mcp=mcp,
        sandbox=sandbox,
        storage=storage,
        api=api,
        stream=stream,
        logging=logging_cfg,
        project_root=root,
        conf_path=conf_path.resolve(),
    )


@lru_cache(maxsize=32)
def _load_settings_cached(resolved_conf_path_str: str) -> Settings:
    path = Path(resolved_conf_path_str)
    data = _load_yaml(path)
    return _build_settings(data, path)


def load_settings(conf_path: str = "conf.yaml") -> Settings:
    resolved = _normalize_conf_path(conf_path)
    return _load_settings_cached(str(resolved))


load_settings.cache_clear = _load_settings_cached.cache_clear  # type: ignore[method-assign]
