from __future__ import annotations

from csbot.uploads.service import AttachmentRow, UploadsService


def build_run_input_with_attachments(
    *,
    message: str,
    attachments: list[AttachmentRow],
    uploads_service: UploadsService,
) -> str:
    text = (message or "").strip()
    sections: list[str] = []

    if attachments:
        sections.append(
            "用户附加了以下文件。系统已在上传阶段完成内容提取，请优先基于提取结果回答；若提取失败，再明确说明限制。"
        )

    for index, row in enumerate(attachments, start=1):
        extracted = (row.extracted_text or "").strip()
        if extracted:
            sections.append(
                "\n".join(
                    [
                        f"[附件{index} | {row.kind}]",
                        f"文件名: {row.filename}",
                        f"媒体类型: {row.media_type}",
                        f"提取状态: {row.extraction_status}",
                        f"提取器: {row.extractor}",
                        "提取内容:",
                        extracted,
                    ]
                )
            )
            continue

        if row.kind == "text":
            preview = uploads_service.read_text_preview(row)
            sections.append(
                "\n".join(
                    [
                        f"[附件{index} | 文本]",
                        f"文件名: {row.filename}",
                        f"媒体类型: {row.media_type}",
                        "文件内容摘录:",
                        preview or "(空文本)",
                    ]
                )
            )
            continue

        sections.append(
            "\n".join(
                [
                    f"[附件{index} | 图片/PDF]",
                    f"文件名: {row.filename}",
                    f"媒体类型: {row.media_type}",
                    f"提取状态: {row.extraction_status}",
                    f"提取器: {row.extractor}",
                    f"提取错误: {row.extraction_error or '(无详细错误)'}",
                    f"文件路径: {row.stored_path}",
                    f"处理提示: {row.ocr_mode}",
                    "说明: 该附件在上传时尝试通过 skills/image-by-intent 提取，但当前未得到可用文本。",
                ]
            )
        )

    if text:
        sections.append(f"用户问题:\n{text}")
    elif attachments:
        sections.append("用户没有额外文本，请先读取附件并给出简明总结。")

    return "\n\n".join(part for part in sections if part.strip()).strip()
