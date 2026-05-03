"""Unit tests for logging_config (local file + rotation parsing)."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from dataclasses import replace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.config.settings import load_settings
from csbot.config_repository.seed import default_runtime_seed
from csbot.logging_config import _parse_rotation, configure_logging
from tests.support.sqlite_config import write_runtime_db


def test_parse_rotation_defaults() -> None:
    b, n = _parse_rotation("")
    assert b == 10 * 1024 * 1024
    assert n == 7


def test_parse_rotation_mb() -> None:
    b, _ = _parse_rotation("3 MB")
    assert b == 3 * 1024 * 1024


def test_parse_rotation_raw_bytes() -> None:
    b, _ = _parse_rotation("8192")
    assert b == 8192


def test_configure_logging_writes_file(tmp_path: Path) -> None:
    load_settings.cache_clear()
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path, seed=default_runtime_seed(tmp_path))
    settings = load_settings(str(db))
    settings = replace(
        settings,
        logging=replace(settings.logging, file_path=str((tmp_path / "logs" / "unit.log").resolve()), rotate_policy="1 MB"),
    )
    configure_logging(settings)

    logging.getLogger("unit_test_logger").info("marker_line_xyz")
    log_file = tmp_path / "logs" / "unit.log"
    assert log_file.is_file()
    text = log_file.read_text(encoding="utf-8")
    assert "marker_line_xyz" in text
    assert "unit_test_logger" in text
