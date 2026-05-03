from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .runtime_repository import (
    RuntimeAgentConfigRecord,
    RuntimeAgentProfileRecord,
    RuntimeAuthRecord,
    RuntimeConfigRepository,
    RuntimeLlmRecord,
    RuntimeMcpConfigRecord,
    RuntimeMcpServerRecord,
)
from .schema import SCHEMA_SQL
from .seed import RuntimeSeedBundle, default_runtime_seed, now_iso


class SqliteRuntimeConfigRepository(RuntimeConfigRepository):
    def __init__(self, db_path: str, *, project_root: Path) -> None:
        self._db_path = Path(db_path).expanduser().resolve()
        self._project_root = project_root.resolve()

    def ensure_ready(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            llm_count = conn.execute("SELECT COUNT(*) FROM runtime_llm_config").fetchone()[0]
            if llm_count == 0:
                self._apply_seed(conn, default_runtime_seed(self._project_root))
            conn.commit()

    def load_llm_config(self) -> RuntimeLlmRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT provider, model, base_url, api_key, temperature, timeout_sec, max_tokens
                FROM runtime_llm_config
                WHERE id = 1
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("runtime_llm_config is empty")
        return RuntimeLlmRecord(
            provider=row["provider"],
            model=row["model"],
            base_url=row["base_url"],
            api_key=row["api_key"],
            temperature=row["temperature"],
            timeout_sec=row["timeout_sec"],
            max_tokens=row["max_tokens"],
        )

    def load_agent_config(self) -> RuntimeAgentConfigRecord:
        with self._connect() as conn:
            config_row = conn.execute(
                """
                SELECT skill_manager_root, thread_pool_workers, default_profile_id
                FROM runtime_agent_config
                WHERE id = 1
                """
            ).fetchone()
            profile_rows = conn.execute(
                """
                SELECT agent_id, name, system_prompt, memory_files_json, skills_sources_json, enabled, is_default
                FROM agent_profiles
                WHERE enabled = 1
                ORDER BY is_default DESC, agent_id ASC
                """
            ).fetchall()
        if config_row is None:
            raise RuntimeError("runtime_agent_config is empty")
        profiles = [
            RuntimeAgentProfileRecord(
                agent_id=row["agent_id"],
                name=row["name"],
                system_prompt=row["system_prompt"],
                memory_files=self._load_json_list(row["memory_files_json"]),
                skills_sources=self._load_json_list(row["skills_sources_json"]),
                enabled=bool(row["enabled"]),
                is_default=bool(row["is_default"]),
            )
            for row in profile_rows
        ]
        return RuntimeAgentConfigRecord(
            skill_manager_root=config_row["skill_manager_root"],
            thread_pool_workers=config_row["thread_pool_workers"],
            default_profile_id=config_row["default_profile_id"],
            profiles=profiles,
        )

    def load_mcp_config(self) -> RuntimeMcpConfigRecord:
        with self._connect() as conn:
            config_row = conn.execute(
                """
                SELECT enabled, startup_timeout_sec
                FROM mcp_runtime_config
                WHERE id = 1
                """
            ).fetchone()
            server_rows = conn.execute(
                """
                SELECT name, transport, command, args_json, url, env_json, enabled
                FROM mcp_servers
                WHERE enabled = 1
                ORDER BY name ASC
                """
            ).fetchall()
        if config_row is None:
            raise RuntimeError("mcp_runtime_config is empty")
        servers = [
            RuntimeMcpServerRecord(
                name=row["name"],
                transport=row["transport"],
                command=row["command"],
                args=self._load_json_list(row["args_json"]),
                url=row["url"],
                env=self._load_json_dict(row["env_json"]),
                enabled=bool(row["enabled"]),
            )
            for row in server_rows
        ]
        return RuntimeMcpConfigRecord(
            enabled=bool(config_row["enabled"]),
            startup_timeout_sec=config_row["startup_timeout_sec"],
            servers=servers,
        )

    def load_auth_config(self) -> RuntimeAuthRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT admin_email, password_hash, admin_name, access_ttl_minutes
                FROM auth_config
                WHERE id = 1
                """
            ).fetchone()
        if row is None:
            raise RuntimeError("auth_config is empty")
        return RuntimeAuthRecord(
            admin_email=row["admin_email"],
            password_hash=row["password_hash"],
            admin_name=row["admin_name"],
            access_ttl_minutes=row["access_ttl_minutes"],
        )

    def replace_all(
        self,
        *,
        llm: RuntimeLlmRecord,
        agent: RuntimeAgentConfigRecord,
        mcp: RuntimeMcpConfigRecord,
        auth: RuntimeAuthRecord,
    ) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._apply_seed(conn, RuntimeSeedBundle(llm=llm, agent=agent, mcp=mcp, auth=auth))
            conn.commit()

    def _apply_seed(self, conn: sqlite3.Connection, bundle: RuntimeSeedBundle) -> None:
        ts = now_iso()
        conn.execute("DELETE FROM runtime_llm_config")
        conn.execute("DELETE FROM runtime_agent_config")
        conn.execute("DELETE FROM agent_profiles")
        conn.execute("DELETE FROM mcp_runtime_config")
        conn.execute("DELETE FROM mcp_servers")
        conn.execute("DELETE FROM auth_config")
        conn.execute(
            """
            INSERT INTO runtime_llm_config
                (id, provider, model, base_url, api_key, temperature, timeout_sec, max_tokens, updated_at)
            VALUES
                (1, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bundle.llm.provider,
                bundle.llm.model,
                bundle.llm.base_url,
                bundle.llm.api_key,
                bundle.llm.temperature,
                bundle.llm.timeout_sec,
                bundle.llm.max_tokens,
                ts,
            ),
        )
        conn.execute(
            """
            INSERT INTO runtime_agent_config
                (id, skill_manager_root, thread_pool_workers, default_profile_id, updated_at)
            VALUES
                (1, ?, ?, ?, ?)
            """,
            (
                bundle.agent.skill_manager_root,
                bundle.agent.thread_pool_workers,
                bundle.agent.default_profile_id,
                ts,
            ),
        )
        for profile in bundle.agent.profiles:
            conn.execute(
                """
                INSERT INTO agent_profiles
                    (agent_id, name, system_prompt, memory_files_json, skills_sources_json, enabled, is_default, created_at, updated_at)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.agent_id,
                    profile.name,
                    profile.system_prompt,
                    json.dumps(profile.memory_files, ensure_ascii=True),
                    json.dumps(profile.skills_sources, ensure_ascii=True),
                    1 if profile.enabled else 0,
                    1 if profile.is_default else 0,
                    ts,
                    ts,
                ),
            )
        conn.execute(
            """
            INSERT INTO mcp_runtime_config
                (id, enabled, startup_timeout_sec, updated_at)
            VALUES
                (1, ?, ?, ?)
            """,
            (
                1 if bundle.mcp.enabled else 0,
                bundle.mcp.startup_timeout_sec,
                ts,
            ),
        )
        for server in bundle.mcp.servers:
            conn.execute(
                """
                INSERT INTO mcp_servers
                    (name, transport, command, args_json, url, env_json, enabled, updated_at)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    server.name,
                    server.transport,
                    server.command,
                    json.dumps(server.args, ensure_ascii=True),
                    server.url,
                    json.dumps(server.env, ensure_ascii=True),
                    1 if server.enabled else 0,
                    ts,
                ),
            )
        conn.execute(
            """
            INSERT INTO auth_config
                (id, admin_email, password_hash, admin_name, access_ttl_minutes, updated_at)
            VALUES
                (1, ?, ?, ?, ?, ?)
            """,
            (
                bundle.auth.admin_email,
                bundle.auth.password_hash,
                bundle.auth.admin_name,
                bundle.auth.access_ttl_minutes,
                ts,
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _load_json_list(payload: str) -> list[str]:
        data = json.loads(payload or "[]")
        if not isinstance(data, list):
            raise RuntimeError("Expected JSON list")
        return [str(item) for item in data]

    @staticmethod
    def _load_json_dict(payload: str) -> dict[str, str]:
        data = json.loads(payload or "{}")
        if not isinstance(data, dict):
            raise RuntimeError("Expected JSON dict")
        return {str(k): str(v) for k, v in data.items()}
