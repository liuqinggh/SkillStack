"""Unit tests: runtime input validation."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.config.settings import load_settings
from csbot.domain.errors import ValidationError
from csbot.runtime.lifecycle import validate_run_message
from tests.support.sqlite_config import write_runtime_db


@pytest.fixture
def settings(tmp_path: Path):
    load_settings.cache_clear()
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path)
    settings = load_settings(str(db))
    settings.api.max_request_chars = 10
    return settings


def test_validate_run_message_strips_and_returns(settings) -> None:
    assert validate_run_message(settings, "  hi  ") == "hi"


def test_validate_run_message_empty_raises(settings) -> None:
    with pytest.raises(ValidationError, match="不能为空"):
        validate_run_message(settings, "")


def test_validate_run_message_whitespace_only_raises(settings) -> None:
    with pytest.raises(ValidationError, match="不能为空"):
        validate_run_message(settings, "   \t  ")


def test_validate_run_message_too_long_raises(settings) -> None:
    with pytest.raises(ValidationError, match="过长"):
        validate_run_message(settings, "x" * 11)
