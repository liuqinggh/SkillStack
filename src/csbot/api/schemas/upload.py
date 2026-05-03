from __future__ import annotations

from pydantic import BaseModel, Field


class UploadSummary(BaseModel):
    attachment_id: str = Field(..., description="Uploaded attachment identifier")
    session_id: str = Field(..., description="Session this attachment belongs to")
    filename: str = Field(..., description="Sanitized filename")
    media_type: str = Field(..., description="Detected media type")
    size_bytes: int = Field(..., description="Saved file size")
    kind: str = Field(..., description="Attachment processing mode: text or ocr")
    ocr_mode: str = Field(..., description="OCR mode requested by the client")
    extraction_status: str = Field(..., description="Extraction status: ready/failed")
    extractor: str = Field(..., description="Extractor used for this attachment")
    extraction_error: str | None = Field(default=None, description="Extraction error when status=failed")
