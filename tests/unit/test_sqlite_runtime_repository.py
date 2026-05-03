from pathlib import Path
import sys
import textwrap

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.config.settings import load_settings
from csbot.config_repository.seed import default_runtime_seed, hash_password
from csbot.config_repository.sqlite_runtime_repository import SqliteRuntimeConfigRepository
from csbot.config_repository.yaml_import import load_runtime_seed_from_yaml
from tests.support.sqlite_config import write_runtime_db


def test_sqlite_repository_round_trips_runtime_seed(tmp_path: Path) -> None:
    db = tmp_path / "runtime.sqlite"
    seed = default_runtime_seed(tmp_path)
    write_runtime_db(db, project_root=tmp_path, seed=seed)

    repo = SqliteRuntimeConfigRepository(str(db), project_root=tmp_path)
    repo.ensure_ready()
    llm = repo.load_llm_config()
    agent = repo.load_agent_config()
    auth = repo.load_auth_config()

    assert llm.model == seed.llm.model
    assert agent.default_profile_id == seed.agent.default_profile_id
    assert {p.agent_id for p in agent.profiles} == {p.agent_id for p in seed.agent.profiles}
    assert auth.password_hash == seed.auth.password_hash


def test_load_settings_exposes_auth_and_bootstrap_db_path(tmp_path: Path) -> None:
    load_settings.cache_clear()
    db = write_runtime_db(tmp_path / "runtime.sqlite", project_root=tmp_path)
    settings = load_settings(str(db))

    assert settings.bootstrap_db_path == db.resolve()
    assert settings.auth.admin_email == "admin@admin.com"
    assert settings.auth.password_hash == hash_password("123456")


def test_load_runtime_seed_from_yaml_hashes_password(tmp_path: Path) -> None:
    conf = tmp_path / "conf.yaml"
    conf.write_text(
        textwrap.dedent(
            """
            llm:
              provider: litellm
              model: gpt-4
              base_url: http://127.0.0.1:4000/v1
              api_key: sk-test
              temperature: 0.5
              timeout_sec: 30
              max_tokens: 1000
            agent:
              skill_manager_root: .
              thread_pool_workers: 2
              default_profile_id: default
              profiles:
                default:
                  skills_sources: [skills]
                  memory_files: [m.json]
                  system_prompt: hello
            mcp:
              enabled: false
              startup_timeout_sec: 20
              servers: []
            auth:
              admin_email: demo@example.com
              admin_password: "secret123"
              admin_name: Demo
              access_ttl_minutes: 60
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    seed = load_runtime_seed_from_yaml(str(conf))

    assert seed.llm.model == "gpt-4"
    assert seed.agent.default_profile_id == "default"
    assert seed.auth.admin_email == "demo@example.com"
    assert seed.auth.password_hash == hash_password("secret123")
