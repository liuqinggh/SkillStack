from __future__ import annotations

from pathlib import Path

from csbot.config.settings import (
    AgentConfig,
    AgentProfileConfig,
    ApiConfig,
    AppConfig,
    AuthConfig,
    LoggingConfig,
    LlmConfig,
    McpConfig,
    McpServerConfig,
    SandboxConfig,
    Settings,
    StorageConfig,
    StreamConfig,
)
from csbot.domain.errors import ConfigError

from .runtime_repository import (
    RuntimeAgentConfigRecord,
    RuntimeAuthRecord,
    RuntimeLlmRecord,
    RuntimeMcpConfigRecord,
)


def assemble_settings(
    *,
    db_path: Path,
    project_root: Path,
    llm: RuntimeLlmRecord,
    agent: RuntimeAgentConfigRecord,
    mcp: RuntimeMcpConfigRecord,
    auth: RuntimeAuthRecord,
) -> Settings:
    try:
        app = AppConfig(
            name="Demo CS Bot API",
            version="0.2.0",
            host="0.0.0.0",
            port=8888,
            debug=False,
        )
        llm_cfg = LlmConfig(
            provider=llm.provider,
            model=llm.model,
            base_url=llm.base_url,
            api_key=llm.api_key,
            temperature=float(llm.temperature),
            timeout_sec=int(llm.timeout_sec),
            max_tokens=int(llm.max_tokens),
        )
        profiles = {
            row.agent_id: AgentProfileConfig(
                skills_sources=row.skills_sources,
                memory_files=row.memory_files,
                system_prompt=row.system_prompt,
            )
            for row in agent.profiles
            if row.enabled
        }
        agent_cfg = AgentConfig(
            skill_manager_root=str(Path(agent.skill_manager_root).expanduser().resolve()),
            thread_pool_workers=int(agent.thread_pool_workers),
            default_profile_id=agent.default_profile_id,
            profiles=profiles,
        )
        mcp_cfg = McpConfig(
            enabled=bool(mcp.enabled),
            startup_timeout_sec=int(mcp.startup_timeout_sec),
            servers=[
                McpServerConfig(
                    name=server.name,
                    transport=server.transport,
                    command=server.command,
                    args=server.args,
                    url=server.url,
                    env=server.env,
                )
                for server in mcp.servers
                if server.enabled
            ],
        )
    except (TypeError, ValueError) as e:
        raise ConfigError(f"Invalid runtime configuration value: {e}") from e
    sandbox = SandboxConfig(
        root_dir=str(project_root.resolve()),
        virtual_mode=True,
        execute_timeout_sec=60,
        max_output_chars=10000,
    )
    storage = StorageConfig(
        session_jsonl_path=str((project_root / "data" / "chat_sessions.jsonl").resolve()),
        flush_mode="immediate",
    )
    api = ApiConfig(
        cors_allow_origins=["*"],
        max_request_chars=20000,
        chat_timeout_sec=120,
    )
    stream = StreamConfig(
        sse_enabled=True,
        heartbeat_sec=15,
        chunk_strategy="delta",
    )
    logging_cfg = LoggingConfig(
        level="INFO",
        format="text",
        file_path=str((project_root / "logs" / "app.log").resolve()),
        rotate_policy="10 MB",
    )
    auth_cfg = AuthConfig(
        admin_email=auth.admin_email,
        password_hash=auth.password_hash,
        admin_name=auth.admin_name,
        access_ttl_minutes=int(auth.access_ttl_minutes),
    )

    _validate_settings(app, llm_cfg, agent_cfg, mcp_cfg, sandbox)
    return Settings(
        app=app,
        llm=llm_cfg,
        agent=agent_cfg,
        mcp=mcp_cfg,
        sandbox=sandbox,
        storage=storage,
        api=api,
        stream=stream,
        logging=logging_cfg,
        auth=auth_cfg,
        project_root=project_root.resolve(),
        bootstrap_db_path=db_path.resolve(),
    )


def _validate_settings(
    app: AppConfig,
    llm: LlmConfig,
    agent: AgentConfig,
    mcp: McpConfig,
    sandbox: SandboxConfig,
) -> None:
    if app.port <= 0 or app.port > 65535:
        raise ConfigError("app.port must be in range 1..65535")
    if not (0.0 <= llm.temperature <= 2.0):
        raise ConfigError("llm.temperature must be between 0 and 2")
    if llm.provider != "litellm":
        raise ConfigError(f'llm.provider must be "litellm" for runtime phase 1 (got {llm.provider!r})')
    if llm.timeout_sec < 1:
        raise ConfigError("llm.timeout_sec must be >= 1")
    if llm.max_tokens < 1:
        raise ConfigError("llm.max_tokens must be >= 1")
    if agent.default_profile_id not in agent.profiles:
        raise ConfigError(f"agent.default_profile_id '{agent.default_profile_id}' not found in agent.profiles")
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
