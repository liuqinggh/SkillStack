from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pytest

from csbot.config.settings import LlmConfig, load_settings
from csbot.config_repository.seed import default_runtime_seed
from csbot.domain.errors import ConfigError

from tests.support.sqlite_config import with_llm, write_runtime_db


def test_settings_rejects_non_litellm_provider(tmp_path: Path) -> None:
    load_settings.cache_clear()
    db = tmp_path / "db.sqlite"
    seed = with_llm(default_runtime_seed(tmp_path), provider="openai")
    write_runtime_db(db, project_root=tmp_path, seed=seed)
    with pytest.raises(ConfigError, match="litellm"):
        load_settings(str(db))


def test_litellm_provider_exposes_openai_compatible_model_kwargs() -> None:
    from csbot.providers import LiteLLMProvider

    cfg = LlmConfig(
        provider="litellm",
        model="gemini-2.5-flash",
        base_url="http://127.0.0.1:4000/v1",
        api_key="sk-x",
        temperature=0.2,
        timeout_sec=45,
        max_tokens=4096,
    )
    provider = LiteLLMProvider(cfg)
    kwargs = provider.openai_compatible_model_kwargs()
    assert kwargs == {
        "model": "gemini-2.5-flash",
        "base_url": "http://127.0.0.1:4000/v1",
        "api_key": "sk-x",
        "temperature": 0.2,
        "timeout": 45,
        "max_tokens": 4096,
    }
