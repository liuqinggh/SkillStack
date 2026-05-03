from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from csbot.api.deps import AppContext
from csbot.api.schemas.upload import UploadSummary
from csbot.domain.errors import ValidationError


def create_uploads_router(context: AppContext) -> APIRouter:
    router = APIRouter(prefix="/api/runtime", tags=["uploads"])

    @router.post("/uploads", response_model=UploadSummary)
    async def create_upload(
        session_id: str = Form(...),
        ocr_mode: str = Form("auto"),
        file: UploadFile = File(...),
    ) -> UploadSummary:
        if context.sessions_service.get_summary(session_id) is None:
            raise HTTPException(status_code=404, detail="Session not found")

        content = await file.read()
        try:
            row = context.uploads_service.save_attachment(
                session_id=session_id,
                filename=file.filename or "upload.bin",
                media_type=file.content_type or "application/octet-stream",
                content=content,
                ocr_mode=ocr_mode,
            )
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        return UploadSummary(
            attachment_id=row.attachment_id,
            session_id=row.session_id,
            filename=row.filename,
            media_type=row.media_type,
            size_bytes=row.size_bytes,
            kind=row.kind,
            ocr_mode=row.ocr_mode,
            extraction_status=row.extraction_status,
            extractor=row.extractor,
            extraction_error=row.extraction_error,
        )

    return router
