from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from csbot.config.settings import load_settings
from tests.support.sqlite_config import write_runtime_db
from csbot.uploads.service import InMemoryAttachmentRepository, UploadsService


def test_save_text_attachment_generates_inline_extraction(tmp_path: Path) -> None:
    load_settings.cache_clear()
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path)
    settings = load_settings(str(db))
    service = UploadsService(settings, InMemoryAttachmentRepository())

    row = service.save_attachment(
        session_id="sess1",
        filename="a.txt",
        media_type="text/plain",
        content="hello world".encode("utf-8"),
    )
    assert row.kind == "text"
    assert row.extraction_status == "ready"
    assert row.extractor == "inline-text-preview"
    assert "hello world" in row.extracted_text


def test_save_ocr_attachment_uses_image_by_intent_extractor(tmp_path: Path, monkeypatch) -> None:
    load_settings.cache_clear()
    db = write_runtime_db(tmp_path / "db.sqlite", project_root=tmp_path)
    settings = load_settings(str(db))
    service = UploadsService(settings, InMemoryAttachmentRepository())

    def _fake_extract(row):
        return f"parsed::{row.filename}"

    monkeypatch.setattr(service, "_extract_with_image_by_intent", _fake_extract)
    row = service.save_attachment(
        session_id="sess1",
        filename="doc.pdf",
        media_type="application/pdf",
        content=b"%PDF-1.4 fake",
    )
    assert row.kind == "ocr"
    assert row.extraction_status == "ready"
    assert row.extractor == "skill:image-by-intent"
    assert row.extracted_text == "parsed::doc.pdf"
