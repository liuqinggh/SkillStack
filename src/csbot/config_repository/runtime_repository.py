from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RuntimeLlmRecord:
    provider: str
    model: str
    base_url: str
    api_key: str
    temperature: float
    timeout_sec: int
    max_tokens: int


@dataclass(frozen=True)
class RuntimeAgentProfileRecord:
    agent_id: str
    name: str
    system_prompt: str
    memory_files: list[str]
    skills_sources: list[str]
    enabled: bool
    is_default: bool


@dataclass(frozen=True)
class RuntimeAgentConfigRecord:
    skill_manager_root: str
    thread_pool_workers: int
    default_profile_id: str
    profiles: list[RuntimeAgentProfileRecord]


@dataclass(frozen=True)
class RuntimeMcpServerRecord:
    name: str
    transport: str
    command: str | None
    args: list[str]
    url: str | None
    env: dict[str, str]
    enabled: bool


@dataclass(frozen=True)
class RuntimeMcpConfigRecord:
    enabled: bool
    startup_timeout_sec: int
    servers: list[RuntimeMcpServerRecord]


@dataclass(frozen=True)
class RuntimeAuthRecord:
    admin_email: str
    password_hash: str
    admin_name: str
    access_ttl_minutes: int


class RuntimeConfigRepository(Protocol):
    def ensure_ready(self) -> None: ...

    def load_llm_config(self) -> RuntimeLlmRecord: ...

    def load_agent_config(self) -> RuntimeAgentConfigRecord: ...

    def load_mcp_config(self) -> RuntimeMcpConfigRecord: ...

    def load_auth_config(self) -> RuntimeAuthRecord: ...

    def replace_all(
        self,
        *,
        llm: RuntimeLlmRecord,
        agent: RuntimeAgentConfigRecord,
        mcp: RuntimeMcpConfigRecord,
        auth: RuntimeAuthRecord,
    ) -> None: ...
