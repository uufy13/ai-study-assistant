"""DOCX 文件解析器（python-docx）。"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document as _DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from ._common import check_ooxml_zip, iso_datetime, make_markdown_table, normalize_text
from .document import Document
from .errors import FileReadError, InvalidDocumentError


class DocxParser:
    """解析 .docx 文件，输出 Markdown 风格扁平文本 Document。

    按文档顺序遍历段落与表格；标题用 ``#`` 层级标记，列表保留 bullet/编号，
    表格输出 Markdown 表格，超链接转 ``[text](url)``，文档属性进入 metadata。
    """

    def parse(self, path: Path) -> Document:
        if not path.exists():
            raise FileReadError(f"File not found: {path}")

        check_ooxml_zip(path, "DOCX")

        try:
            doc = _DocxDocument(str(path))
        except Exception as exc:  # python-docx 对损坏文件的异常种类不统一
            raise InvalidDocumentError(f"Failed to parse DOCX: {path}") from exc

        blocks: list[str] = []
        table_count = 0
        for block in _iter_block_items(doc):
            if isinstance(block, Paragraph):
                rendered = self._render_paragraph(block)
            else:
                rendered = self._render_table(block)
                if rendered:
                    table_count += 1
            if rendered:
                blocks.append(rendered)

        content = normalize_text("\n\n".join(blocks))
        metadata = _build_metadata(doc, table_count)
        return Document(source=path, format="docx", content=content, metadata=metadata)

    def _render_paragraph(self, paragraph: Paragraph) -> str:
        text = _paragraph_text(paragraph).strip()
        if not text:
            return ""
        style_name = paragraph.style.name if paragraph.style is not None else ""
        lowered = style_name.lower()

        if "heading" in lowered or "标题" in style_name:
            return "#" * _heading_level(style_name) + " " + text
        if "bullet" in lowered or "项目符号" in style_name:
            return "- " + text
        if "number" in lowered or "编号" in style_name:
            return "1. " + text
        return text

    @staticmethod
    def _render_table(table: Table) -> str:
        rows: list[list[str]] = []
        for row in table.rows:
            rows.append([cell.text for cell in row.cells])
        return make_markdown_table(rows)


def _iter_block_items(doc):
    """按文档顺序产出 Paragraph 与 Table（python-docx 官方配方）。"""
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def _paragraph_text(paragraph: Paragraph) -> str:
    """按顺序拼接普通 run 与超链接文本，超链接转 ``[text](url)``。"""
    parts: list[str] = []
    for child in paragraph._p.iterchildren():
        if child.tag == qn("w:hyperlink"):
            parts.append(_hyperlink_text(paragraph, child))
        elif child.tag == qn("w:r"):
            parts.append(_run_text(child))
    if parts:
        return "".join(parts)
    return paragraph.text


def _run_text(run) -> str:
    return "".join(node.text or "" for node in run.iter(qn("w:t")))


def _hyperlink_text(paragraph: Paragraph, hyperlink) -> str:
    text = "".join(node.text or "" for node in hyperlink.iter(qn("w:t")))
    url = ""
    rid = hyperlink.get(qn("r:id"))
    if rid:
        try:
            url = paragraph.part.rels[rid].target_ref or ""
        except KeyError:
            url = ""
    if url:
        return f"[{text}]({url})"
    return text


def _heading_level(style_name: str) -> int:
    match = re.search(r"(\d+)\s*$", style_name.strip())
    if match:
        return max(1, min(int(match.group(1)), 6))
    return 1


def _build_metadata(doc, table_count: int) -> dict:
    metadata: dict = {
        "parser_name": "docx",
        "parser_version": "0.2.0",
        "table_count": table_count,
    }
    try:
        cp = doc.core_properties
        fields = {
            "title": cp.title,
            "author": cp.author,
            "created_at": iso_datetime(cp.created),
            "modified_at": iso_datetime(cp.modified),
        }
    except Exception:  # noqa: BLE001 - 核心属性缺失时不致命
        fields = {}
    for key, value in fields.items():
        if value:
            metadata[key] = value
    return metadata
