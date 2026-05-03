from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.config.settings import DEFAULT_DB_PATH
from csbot.config_repository.seed import default_runtime_seed
from csbot.config_repository.sqlite_runtime_repository import SqliteRuntimeConfigRepository
from csbot.config_repository.yaml_import import load_runtime_seed_from_yaml


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate runtime config from YAML into SQLite.")
    parser.add_argument("--from-yaml", dest="yaml_path", required=True, help="Path to the source conf.yaml")
    parser.add_argument("--to-db", dest="db_path", default=DEFAULT_DB_PATH, help="Target SQLite DB path")
    parser.add_argument("--backup", action="store_true", help="Backup existing SQLite file before overwriting")
    args = parser.parse_args()

    yaml_path = Path(args.yaml_path).expanduser().resolve()
    db_path = Path(args.db_path).expanduser().resolve()
    if db_path.exists() and args.backup:
        backup_path = db_path.with_suffix(db_path.suffix + ".bak")
        shutil.copy2(db_path, backup_path)
        print(f"Backed up existing DB to {backup_path}")

    seed = load_runtime_seed_from_yaml(str(yaml_path))
    repo = SqliteRuntimeConfigRepository(str(db_path), project_root=PROJECT_ROOT)
    repo.ensure_ready()
    repo.replace_all(llm=seed.llm, agent=seed.agent, mcp=seed.mcp, auth=seed.auth)

    current = SqliteRuntimeConfigRepository(str(db_path), project_root=PROJECT_ROOT)
    current.ensure_ready()
    agent_ids = [profile.agent_id for profile in current.load_agent_config().profiles]
    print(f"Migrated YAML config from {yaml_path} to {db_path}")
    print(f"Agents: {agent_ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
