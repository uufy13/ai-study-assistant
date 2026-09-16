"""PDF 文件解析器（PyMuPDF）。

依赖许可：PyMuPDF（导入名 ``pymupdf``）采用 AGPL-3.0 许可证。本工具仅将其
作为运行时库做只读文本提取，不修改、不重新分发其源码或二进制。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pymupdf

from ._common import normalize_text
from .document import Document
from .errors import FileReadError, InvalidDocumentError, PasswordProtectedError


class PdfParser:
    """解析 .pdf 文件，输出带页码分隔的 Markdown 风格文本 Document。

    仅支持文本型 PDF（含可提取的嵌入文本）。扫描型 PDF 不实现 OCR，文本提取
    为空，通过 metadata 的 ``has_text`` 标记。加密 PDF 抛 ``PasswordProtectedError``。
    """

    def parse(self, path: Path) -> Document:
        if not path.exists():
            raise FileReadError(f"File not found: {path}")

        try:
            doc = pymupdf.open(str(path))
        except Exception as exc:  # 损坏 PDF 打开异常
            raise InvalidDocumentError(f"Failed to open PDF: {path}") from exc

        try:
            if doc.needs_pass:
                raise PasswordProtectedError(f"PDF is password-protected: {path}")
            return self._build(path, doc)
        finally:
            doc.close()

    def _build(self, path: Path, doc) -> Document:
        page_count = doc.page_count
        blocks: list[str] = []
        table_count = 0
        has_text = False

        for index in range(page_count):
            page = doc.load_page(index)
            tables, table_bboxes = _extract_tables(page)
            text = _extract_text(page, exclude_bboxes=table_bboxes)

            parts: list[str] = []
            if text:
                parts.append(text)
            parts.extend(tables)
            table_count += len(tables)

            if parts:
                has_text = True
                blocks.append(f"--- Page {index + 1} ---")
                blocks.extend(parts)

        content = normalize_text("\n\n".join(blocks))
        metadata = _build_metadata(doc, page_count, has_text, table_count)
        return Document(source=path, format="pdf", content=content, metadata=metadata)


def _extract_text(page, exclude_bboxes=None) -> str:
    """按阅读顺序（上→下、左→右）提取页面文本，支持多栏布局。

    ``get_text("text")`` 默认按内容流顺序输出（多栏时会按列串接），改用
    ``get_text("blocks")`` 后按 (y, x) 排序得到视觉阅读顺序。表格区域内的
    单元格文本会被排除（表格另作 Markdown 输出，避免重复）。
    """
    text_blocks = page.get_text("blocks")
    if exclude_bboxes:
        text_blocks = [
            b for b in text_blocks if not _inside_any_bbox(b, exclude_bboxes)
        ]
    text_blocks.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
    return "\n".join(b[4].strip() for b in text_blocks if b[4].strip())


def _inside_any_bbox(block, bboxes) -> bool:
    """块中心点是否落在任一表格 bbox 内。"""
    cx = (block[0] + block[2]) / 2
    cy = (block[1] + block[3]) / 2
    return any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in bboxes)


def _extract_tables(page) -> tuple[list[str], list[tuple]]:
    """提取页面表格为 Markdown；检测失败不致命。返回 (markdown, bbox) 列表。"""
    results: list[str] = []
    bboxes: list[tuple] = []
    try:
        for table in page.find_tables().tables:
            markdown = table.to_markdown().strip()
            if markdown:
                results.append(markdown)
                bboxes.append(tuple(table.bbox))
    except Exception:  # noqa: BLE001, S110 - 表格检测失败不致命
        pass
    return results, bboxes


def _build_metadata(doc, page_count: int, has_text: bool, table_count: int) -> dict:
    metadata: dict = {
        "parser_name": "pdf",
        "parser_version": "0.2.0",
        "page_count": page_count,
        "has_text": has_text,
        "table_count": table_count,
    }
    try:
        meta = doc.metadata or {}
        fields = {
            "title": meta.get("title"),
            "author": meta.get("author"),
            "created_at": _parse_pdf_date(meta.get("creationDate")),
            "modified_at": _parse_pdf_date(meta.get("modDate")),
        }
    except Exception:  # noqa: BLE001 - 元数据缺失时不致命
        fields = {}
    for key, value in fields.items():
        if value:
            metadata[key] = value
    return metadata


def _parse_pdf_date(value: object) -> str | None:
    """把 PDF 的 ``D:YYYYMMDDHHmmSS...`` 日期转成 ISO-8601。"""
    if not value:
        return None
    text = str(value)
    text = text.removeprefix("D:")
    match = re.match(r"(\d{14})", text)
    if not match:
        return None
    try:
        # PDF 日期时区解析为 best-effort
        return datetime.strptime(match.group(1), "%Y%m%d%H%M%S").isoformat()  # noqa: DTZ007
    except ValueError:
        return None
