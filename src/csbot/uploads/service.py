from __future__ import annotations

from dataclasses import replace
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import os
import re
import shutil
import subprocess
import uuid

from csbot.config.settings import Settings
from csbot.domain.errors import ValidationError

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".yaml",
    ".yml",
    ".log",
}
OCR_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_TEXT_ATTACHMENT_CHARS = 4000


@dataclass(frozen=True)
class AttachmentRow:
    attachment_id: str
    session_id: str
    filename: str
    media_type: str
    stored_path: str
    size_bytes: int
    kind: str
    ocr_mode: str
    extraction_status: str = "pending"
    extracted_text: str = ""
    extractor: str = "none"
    extraction_error: str | None = None


class AttachmentRepository(Protocol):
    def save(self, row: AttachmentRow) -> None: ...
    def get(self, attachment_id: str) -> AttachmentRow | None: ...


class InMemoryAttachmentRepository:
    def __init__(self) -> None:
        self._rows: dict[str, AttachmentRow] = {}

    def save(self, row: AttachmentRow) -> None:
        self._rows[row.attachment_id] = row

    def get(self, attachment_id: str) -> AttachmentRow | None:
        return self._rows.get(attachment_id)


class UploadsService:
    def __init__(self, settings: Settings, repository: AttachmentRepository) -> None:
        self._settings = settings
        self._repo = repository

    def save_attachment(
        self,
        *,
        session_id: str,
        filename: str,
        media_type: str,
        content: bytes,
        ocr_mode: str = "auto",
    ) -> AttachmentRow:
        safe_name = self._safe_filename(filename)
        ext = Path(safe_name).suffix.lower()
        kind = self._detect_kind(ext, media_type)
        size_bytes = len(content)

        if size_bytes <= 0:
            raise ValidationError("上传文件不能为空")
        if size_bytes > MAX_FILE_SIZE_BYTES:
            raise ValidationError(f"文件过大，单文件不能超过 {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB")

        attachment_id = str(uuid.uuid4())
        target_dir = self._upload_root() / session_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{attachment_id}-{safe_name}"
        target_path.write_bytes(content)

        row = AttachmentRow(
            attachment_id=attachment_id,
            session_id=session_id,
            filename=safe_name,
            media_type=media_type or "application/octet-stream",
            stored_path=str(target_path),
            size_bytes=size_bytes,
            kind=kind,
            ocr_mode=(ocr_mode or "auto").strip() or "auto",
        )
        row = self._extract_for_agent(row)
        self._repo.save(row)
        return row

    def get_attachment(self, attachment_id: str) -> AttachmentRow | None:
        return self._repo.get(attachment_id)

    def read_text_preview(self, row: AttachmentRow, *, max_chars: int = MAX_TEXT_ATTACHMENT_CHARS) -> str:
        path = Path(row.stored_path)
        if not path.is_file():
            raise ValidationError(f"附件文件不存在: {row.filename}")
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars].strip()

    def _extract_for_agent(self, row: AttachmentRow) -> AttachmentRow:
        if row.kind == "text":
            text = self.read_text_preview(row)
            return replace(
                row,
                extraction_status="ready",
                extracted_text=text,
                extractor="inline-text-preview",
                extraction_error=None,
            )
        try:
            text = self._extract_with_image_by_intent(row)
            if not text:
                return replace(
                    row,
                    extraction_status="failed",
                    extracted_text="",
                    extractor="skill:image-by-intent",
                    extraction_error="image-by-intent 未返回有效文本",
                )
            return replace(
                row,
                extraction_status="ready",
                extracted_text=text[:MAX_TEXT_ATTACHMENT_CHARS],
                extractor="skill:image-by-intent",
                extraction_error=None,
            )
        except Exception as e:
            return replace(
                row,
                extraction_status="failed",
                extracted_text="",
                extractor="skill:image-by-intent",
                extraction_error=str(e),
            )

    def _extract_with_image_by_intent(self, row: AttachmentRow) -> str:
        skill_root = Path(self._settings.agent.skill_manager_root).resolve()
        script_path = skill_root / "skills" / "image-by-intent" / "scripts" / "vision-curl.sh"
        if not script_path.is_file():
            raise ValidationError(f"未找到 image-by-intent 脚本: {script_path}")
        bash = shutil.which("bash")
        if not bash:
            raise ValidationError("当前环境缺少 bash，无法执行 image-by-intent 提取脚本")

        args = [bash, str(script_path), row.stored_path]
        user_prompt = (row.ocr_mode or "auto").strip()
        if user_prompt and user_prompt != "auto":
            args.append(user_prompt)

        env = os.environ.copy()
        env["LITELLM_BASE_URL"] = self._settings.llm.base_url
        env["LITELLM_MODEL"] = self._settings.llm.model
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=max(1, int(self._settings.sandbox.execute_timeout_sec)),
            env=env,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise ValidationError(f"image-by-intent 执行失败: {detail or 'unknown error'}")
        output = (proc.stdout or "").strip()
        if output.startswith("==="):
            lines = output.splitlines()
            output = "\n".join(lines[1:]).strip()
        return output

    def _upload_root(self) -> Path:
        return Path(self._settings.sandbox.root_dir).resolve() / ".demo-csbot" / "uploads"

    @staticmethod
    def _safe_filename(filename: str) -> str:
        raw = Path(filename or "upload.bin").name
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
        return safe or "upload.bin"

    @staticmethod
    def _detect_kind(ext: str, media_type: str) -> str:
        lowered = (media_type or "").lower()
        if ext in TEXT_EXTENSIONS or lowered.startswith("text/") or lowered in {"application/json", "application/x-yaml"}:
            return "text"
        if ext in OCR_EXTENSIONS or lowered == "application/pdf" or lowered.startswith("image/"):
            return "ocr"
        raise ValidationError("暂不支持该文件类型上传")
