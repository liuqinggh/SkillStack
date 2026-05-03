from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.config.settings import DEFAULT_DB_PATH, load_settings
from csbot.config_repository.seed import default_runtime_seed
from csbot.domain.deployment_agent import load_deployment_agent
from csbot.domain.errors import ConfigError

from tests.support.sqlite_config import with_agent, with_llm, write_runtime_db


def test_load_settings_from_default_db():
    load_settings.cache_clear()
    settings = load_settings(DEFAULT_DB_PATH)
    assert settings.app.name
    assert settings.llm.model
    assert settings.agent.profiles
    assert settings.agent.default_profile_id in settings.agent.profiles
    assert settings.sandbox.execute_timeout_sec >= 1


def test_load_settings_relative_path_resolves_against_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    load_settings.cache_clear()
    dir_a = tmp_path / "proj_a"
    dir_b = tmp_path / "proj_b"
    dir_a.mkdir()
    dir_b.mkdir()
    write_runtime_db(dir_a / "db.sqlite", project_root=dir_a)
    write_runtime_db(dir_b / "db.sqlite", project_root=dir_b)

    monkeypatch.chdir(dir_a)
    sa = load_settings("db.sqlite")
    monkeypatch.chdir(dir_b)
    sb = load_settings("db.sqlite")

    assert sa.bootstrap_db_path.resolve() != sb.bootstrap_db_path.resolve()
    assert sa.project_root.resolve() == dir_a.resolve()
    assert sb.project_root.resolve() == dir_b.resolve()


def test_llm_invalid_numeric_fields_raise_config_error(tmp_path: Path) -> None:
    load_settings.cache_clear()
    db = tmp_path / "db.sqlite"
    seed = with_llm(default_runtime_seed(tmp_path), temperature="not-a-float")
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    with pytest.raises(ConfigError, match="Invalid runtime configuration value"):
        load_settings(str(db))

    load_settings.cache_clear()
    seed = with_llm(default_runtime_seed(tmp_path), timeout_sec="x")
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    with pytest.raises(ConfigError, match="Invalid runtime configuration value"):
        load_settings(str(db))

    load_settings.cache_clear()
    seed = with_llm(default_runtime_seed(tmp_path), max_tokens=[])
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    with pytest.raises(ConfigError, match="Invalid runtime configuration value"):
        load_settings(str(db))


def test_llm_timeout_sec_and_max_tokens_lower_bounds(tmp_path: Path) -> None:
    load_settings.cache_clear()
    db = tmp_path / "db.sqlite"
    seed = with_llm(default_runtime_seed(tmp_path), timeout_sec=0)
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    with pytest.raises(ConfigError, match="llm.timeout_sec"):
        load_settings(str(db))

    load_settings.cache_clear()
    seed = with_llm(default_runtime_seed(tmp_path), max_tokens=0)
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    with pytest.raises(ConfigError, match="llm.max_tokens"):
        load_settings(str(db))


def test_agent_profiles_parsing_and_default_resolution(tmp_path: Path) -> None:
    load_settings.cache_clear()
    db = tmp_path / "db.sqlite"
    seed = with_agent(
        default_runtime_seed(tmp_path),
        default_profile_id="claim",
        profiles=[
            default_runtime_seed(tmp_path).agent.profiles[0],
            default_runtime_seed(tmp_path).agent.profiles[1],
        ],
    )
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    settings = load_settings(str(db))
    assert settings.agent.default_profile_id == "claim"
    assert settings.agent.resolve_profile(None).system_prompt == "claim prompt"
    assert settings.agent.resolve_profile("default").system_prompt.startswith("你是一个聪明")
    assert settings.agent.deployment_profile().system_prompt == "claim prompt"
    bundle = load_deployment_agent(settings.agent)
    assert bundle.id == "claim"
    assert bundle.profile.system_prompt == "claim prompt"


def test_mcp_enabled_requires_at_least_one_server(tmp_path: Path) -> None:
    load_settings.cache_clear()
    from dataclasses import replace
    from csbot.config_repository.runtime_repository import RuntimeMcpConfigRecord

    db = tmp_path / "db.sqlite"
    seed = replace(default_runtime_seed(tmp_path), mcp=RuntimeMcpConfigRecord(enabled=True, startup_timeout_sec=20, servers=[]))
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    with pytest.raises(ConfigError, match="mcp.enabled is true but mcp.servers is empty"):
        load_settings(str(db))


def test_mcp_stdio_server_parses(tmp_path: Path) -> None:
    load_settings.cache_clear()
    from dataclasses import replace
    from csbot.config_repository.runtime_repository import RuntimeMcpConfigRecord, RuntimeMcpServerRecord

    db = tmp_path / "db.sqlite"
    seed = replace(
        default_runtime_seed(tmp_path),
        mcp=RuntimeMcpConfigRecord(
            enabled=False,
            startup_timeout_sec=15,
            servers=[
                RuntimeMcpServerRecord(
                    name="fs",
                    transport="stdio",
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-filesystem", "."],
                    url=None,
                    env={"MCP_MODE": "readonly"},
                    enabled=True,
                )
            ],
        ),
    )
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    settings = load_settings(str(db))
    assert settings.mcp.enabled is False
    assert settings.mcp.startup_timeout_sec == 15
    assert len(settings.mcp.servers) == 1
    server = settings.mcp.servers[0]
    assert server.name == "fs"
    assert server.transport == "stdio"
    assert server.command == "npx"
    assert server.args[0] == "-y"
    assert server.env["MCP_MODE"] == "readonly"
