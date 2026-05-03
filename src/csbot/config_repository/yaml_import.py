from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from csbot.domain.errors import ConfigError

from .runtime_repository import (
    RuntimeAgentConfigRecord,
    RuntimeAgentProfileRecord,
    RuntimeAuthRecord,
    RuntimeLlmRecord,
    RuntimeMcpConfigRecord,
    RuntimeMcpServerRecord,
)
from .seed import RuntimeSeedBundle, hash_password


def load_runtime_seed_from_yaml(conf_path: str) -> RuntimeSeedBundle:
    path = Path(conf_path).expanduser().resolve()
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError("Config root must be a mapping")

    root = path.parent
    llm_raw = _required_mapping(data, "llm", "root")
    agent_raw = _required_mapping(data, "agent", "root")
    mcp_raw = data.get("mcp", {})
    auth_raw = data.get("auth", {})
    if not isinstance(mcp_raw, dict):
        raise ConfigError("Config section 'mcp' must be a mapping when present")
    if not isinstance(auth_raw, dict):
        raise ConfigError("Config section 'auth' must be a mapping when present")

    profiles_raw = agent_raw.get("profiles")
    profiles: list[RuntimeAgentProfileRecord] = []
    if isinstance(profiles_raw, dict) and profiles_raw:
        for pid, raw_profile in profiles_raw.items():
            profile = _required_mapping(profiles_raw, pid, "agent.profiles")
            profile_id = str(pid).strip()
            profiles.append(
                RuntimeAgentProfileRecord(
                    agent_id=profile_id,
                    name=_display_name(profile_id, str(agent_raw.get("default_profile_id", "default"))),
                    system_prompt=str(_required(profile, "system_prompt", f"agent.profiles.{profile_id}")),
                    memory_files=_as_list(profile.get("memory_files", []), f"agent.profiles.{profile_id}.memory_files"),
                    skills_sources=_as_list(profile.get("skills_sources", []), f"agent.profiles.{profile_id}.skills_sources"),
                    enabled=True,
                    is_default=False,
                )
            )
    else:
        profiles.append(
            RuntimeAgentProfileRecord(
                agent_id="default",
                name="Default Agent",
                system_prompt=str(_required(agent_raw, "system_prompt", "agent")),
                memory_files=_as_list(agent_raw.get("memory_files", []), "agent.memory_files"),
                skills_sources=_as_list(agent_raw.get("skills_sources", []), "agent.skills_sources"),
                enabled=True,
                is_default=True,
            )
        )

    default_profile_id = str(agent_raw.get("default_profile_id", "default")).strip() or "default"
    for profile in profiles:
        if profile.agent_id == default_profile_id:
            profiles[profiles.index(profile)] = RuntimeAgentProfileRecord(
                agent_id=profile.agent_id,
                name=profile.name,
                system_prompt=profile.system_prompt,
                memory_files=profile.memory_files,
                skills_sources=profile.skills_sources,
                enabled=profile.enabled,
                is_default=True,
            )
    if default_profile_id not in {p.agent_id for p in profiles}:
        raise ConfigError(f"agent.default_profile_id '{default_profile_id}' not found in agent.profiles")

    servers: list[RuntimeMcpServerRecord] = []
    for idx, raw_server in enumerate(mcp_raw.get("servers", [])):
        if not isinstance(raw_server, dict):
            raise ConfigError(f"mcp.servers[{idx}] must be a mapping")
        transport = str(raw_server.get("transport", "stdio")).strip() or "stdio"
        servers.append(
            RuntimeMcpServerRecord(
                name=str(_required(raw_server, "name", f"mcp.servers[{idx}]")),
                transport=transport,
                command=str(raw_server.get("command")).strip() if raw_server.get("command") is not None else None,
                args=_as_str_list(raw_server.get("args", []), f"mcp.servers[{idx}].args"),
                url=str(raw_server.get("url")).strip() if raw_server.get("url") is not None else None,
                env=_as_str_dict(raw_server.get("env", {}), f"mcp.servers[{idx}].env"),
                enabled=True,
            )
        )

    password = str(auth_raw.get("admin_password", "123456"))
    return RuntimeSeedBundle(
        llm=RuntimeLlmRecord(
            provider=str(_required(llm_raw, "provider", "llm")),
            model=str(_required(llm_raw, "model", "llm")),
            base_url=str(_required(llm_raw, "base_url", "llm")),
            api_key=str(_required(llm_raw, "api_key", "llm")),
            temperature=float(_required(llm_raw, "temperature", "llm")),
            timeout_sec=int(_required(llm_raw, "timeout_sec", "llm")),
            max_tokens=int(llm_raw.get("max_tokens", 8192)),
        ),
        agent=RuntimeAgentConfigRecord(
            skill_manager_root=str(Path(str(_required(agent_raw, "skill_manager_root", "agent"))).expanduser().resolve()),
            thread_pool_workers=int(_required(agent_raw, "thread_pool_workers", "agent")),
            default_profile_id=default_profile_id,
            profiles=profiles,
        ),
        mcp=RuntimeMcpConfigRecord(
            enabled=bool(mcp_raw.get("enabled", False)),
            startup_timeout_sec=int(mcp_raw.get("startup_timeout_sec", 20)),
            servers=servers,
        ),
        auth=RuntimeAuthRecord(
            admin_email=str(auth_raw.get("admin_email", "admin@admin.com")),
            password_hash=hash_password(password),
            admin_name=str(auth_raw.get("admin_name", "Admin")),
            access_ttl_minutes=int(auth_raw.get("access_ttl_minutes", 720)),
        ),
    )


def _required(data: dict[str, Any], key: str, parent: str) -> Any:
    if key not in data:
        raise ConfigError(f"Missing required config key: {parent}.{key}")
    return data[key]


def _required_mapping(data: dict[str, Any], key: str, parent: str) -> dict[str, Any]:
    value = _required(data, key, parent)
    if not isinstance(value, dict):
        raise ConfigError(f"{parent}.{key} must be a mapping")
    return value


def _as_list(value: Any, key: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v.strip() for v in value):
        raise ConfigError(f"Config key '{key}' must be a non-empty string list")
    return [v.strip() for v in value]


def _as_str_list(value: Any, key: str) -> list[str]:
    if not isinstance(value, list):
        raise ConfigError(f"Config key '{key}' must be a string list")
    return [str(item) for item in value]


def _as_str_dict(value: Any, key: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"Config key '{key}' must be a string map")
    return {str(k): str(v) for k, v in value.items()}


def _display_name(profile_id: str, default_profile_id: str) -> str:
    if profile_id == default_profile_id:
        return "Default Agent"
    words = profile_id.replace("-", " ").replace("_", " ").split()
    return " ".join(part.capitalize() for part in words) or profile_id
