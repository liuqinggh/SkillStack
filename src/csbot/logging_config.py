"""Configure stdlib logging: console + rotating local file from ``Settings.logging``."""

from __future__ import annotations

import logging
import logging.handlers
import re
from pathlib import Path

from csbot.config.settings import Settings


def _parse_level(level_str: str) -> int:
    name = (level_str or "INFO").strip().upper()
    return getattr(logging, name, logging.INFO)


def _resolve_log_file(settings: Settings) -> Path:
    raw = (settings.logging.file_path or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (settings.project_root / p).resolve()
        return p
    return (settings.project_root / "logs" / "app.log").resolve()


def _parse_rotation(rotate_policy: str) -> tuple[int, int]:
    """Return ``(max_bytes, backup_count)`` for :class:`RotatingFileHandler`.

    Examples: ``""`` → 10 MiB; ``"20 MB"`` → 20 MiB; ``"5242880"`` (digits only) → bytes.
    """
    text = (rotate_policy or "").strip()
    if not text:
        return 10 * 1024 * 1024, 7
    m = re.match(r"^(\d+)\s*(MB|MIB|KB|B)?$", text, re.IGNORECASE)
    if not m:
        return 10 * 1024 * 1024, 7
    n = int(m.group(1))
    unit = m.group(2)
    if unit is None:
        max_bytes = n
    else:
        u = unit.upper()
        if u == "B":
            max_bytes = n
        elif u == "KB":
            max_bytes = n * 1024
        elif u in ("MB", "MIB"):
            max_bytes = n * 1024 * 1024
        else:
            max_bytes = 10 * 1024 * 1024
    return max_bytes, 7


def _formatter(settings: Settings) -> logging.Formatter:
    fmt_kind = (settings.logging.format or "text").strip().lower()
    if fmt_kind == "json":
        fmt = "%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s"
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")


def configure_logging(settings: Settings) -> None:
    """Attach console + rotating file handlers to the root logger."""
    root = logging.root
    for h in root.handlers[:]:
        root.removeHandler(h)

    level = _parse_level(settings.logging.level)
    root.setLevel(level)
    formatter = _formatter(settings)

    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(formatter)
    root.addHandler(stream)

    log_path = _resolve_log_file(settings)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    max_bytes, backup_count = _parse_rotation(settings.logging.rotate_policy)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
