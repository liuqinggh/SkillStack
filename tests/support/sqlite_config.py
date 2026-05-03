from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from csbot.config_repository.seed import RuntimeSeedBundle, default_runtime_seed
from csbot.config_repository.sqlite_runtime_repository import SqliteRuntimeConfigRepository


def write_runtime_db(
    db_path: Path,
    *,
    project_root: Path | None = None,
    seed: RuntimeSeedBundle | None = None,
) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    root = (project_root or db_path.parent).resolve()
    bundle = seed or default_runtime_seed(root)
    repo = SqliteRuntimeConfigRepository(str(db_path), project_root=root)
    repo.ensure_ready()
    repo.replace_all(llm=bundle.llm, agent=bundle.agent, mcp=bundle.mcp, auth=bundle.auth)
    return db_path


def with_llm(seed: RuntimeSeedBundle, **kwargs) -> RuntimeSeedBundle:
    return replace(seed, llm=replace(seed.llm, **kwargs))


def with_agent(seed: RuntimeSeedBundle, **kwargs) -> RuntimeSeedBundle:
    return replace(seed, agent=replace(seed.agent, **kwargs))


def with_auth(seed: RuntimeSeedBundle, **kwargs) -> RuntimeSeedBundle:
    return replace(seed, auth=replace(seed.auth, **kwargs))
