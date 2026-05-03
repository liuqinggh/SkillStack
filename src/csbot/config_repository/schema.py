from __future__ import annotations


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runtime_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_llm_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    base_url TEXT NOT NULL,
    api_key TEXT NOT NULL,
    temperature REAL NOT NULL,
    timeout_sec INTEGER NOT NULL,
    max_tokens INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_agent_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    skill_manager_root TEXT NOT NULL,
    thread_pool_workers INTEGER NOT NULL,
    default_profile_id TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_profiles (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    memory_files_json TEXT NOT NULL,
    skills_sources_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mcp_runtime_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 0,
    startup_timeout_sec INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mcp_servers (
    name TEXT PRIMARY KEY,
    transport TEXT NOT NULL,
    command TEXT,
    args_json TEXT NOT NULL,
    url TEXT,
    env_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    admin_email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    admin_name TEXT NOT NULL,
    access_ttl_minutes INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
"""
