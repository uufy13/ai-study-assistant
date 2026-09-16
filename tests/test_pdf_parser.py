"""PDF Parser 单元测试（虚构、脱敏、最小化 fixture）。"""

import struct
import zlib
from pathlib import Path

import pymupdf
import pytest

from ai_study_assistant.parsers.errors import (
    FileReadError,
    InvalidDocumentError,
    PasswordProtectedError,
)
from ai_study_assistant.parsers.pdf_parser import PdfParser


def _make_png(width: int = 1, height: int = 1) -> bytes:
    """用标准库构造最小合法 PNG（模拟扫描型 PDF 的图片，避免引入 Pillow）。"""

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    raw = b"\x00" + b"\x00\x00\x00\x00" * width  # 每行 filter=0 + RGBA 像素
    idat = zlib.compress(raw * height)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def _save(path: Path, builder) -> Path:
    doc = pymupdf.open()
    builder(doc)
    doc.save(str(path))
    doc.close()
    return path


def _add_table(page, rect, cells) -> None:
    """手绘网格 + 单元格文本，供 ``find_tables`` 识别为表格。"""
    nrows = len(cells)
    ncols = len(cells[0]) if cells else 0
    x0, y0, x1, y1 = rect
    col_w = (x1 - x0) / ncols
    row_h = (y1 - y0) / nrows
    xs = [x0 + i * col_w for i in range(ncols + 1)]
    ys = [y0 + j * row_h for j in range(nrows + 1)]
    for x in xs:
        page.draw_line(pymupdf.Point(x, y0), pymupdf.Point(x, y1))
    for y in ys:
        page.draw_line(pymupdf.Point(x0, y), pymupdf.Point(x1, y))
    for r in range(nrows):
        for c in range(ncols):
            page.insert_textbox(
                pymupdf.Rect(xs[c] + 4, ys[r] + 4, xs[c + 1] - 4, ys[r + 1] - 4),
                cells[r][c],
                fontname="china-s",
            )


def test_parse_pdf_basic(tmp_path: Path) -> None:
    def builder(doc) -> None:
        page1 = doc.new_page()
        page1.insert_textbox(pymupdf.Rect(72, 72, 500, 200), "Chapter 1 Overview")
        page1.insert_textbox(pymupdf.Rect(72, 100, 500, 200), "This is body content.")
        page2 = doc.new_page()
        page2.insert_textbox(pymupdf.Rect(72, 72, 500, 200), "Chapter 2 Details")

    path = _save(tmp_path / "sample.pdf", builder)
    doc = PdfParser().parse(path)

    assert doc.format == "pdf"
    assert "--- Page 1 ---" in doc.content
    assert "Chapter 1 Overview" in doc.content
    assert "--- Page 2 ---" in doc.content
    assert "Chapter 2 Details" in doc.content
    assert doc.metadata["page_count"] == 2
    assert doc.metadata["has_text"] is True
    assert doc.metadata["parser_name"] == "pdf"


def test_parse_pdf_page_order(tmp_path: Path) -> None:
    def builder(doc) -> None:
        p1 = doc.new_page()
        p1.insert_textbox(pymupdf.Rect(72, 72, 500, 200), "第一页内容", fontname="china-s")
        p2 = doc.new_page()
        p2.insert_textbox(pymupdf.Rect(72, 72, 500, 200), "第二页内容", fontname="china-s")

    path = _save(tmp_path / "order.pdf", builder)
    doc = PdfParser().parse(path)

    content = doc.content
    assert content.index("--- Page 1 ---") < content.index("第一页内容")
    assert content.index("第一页内容") < content.index("--- Page 2 ---")
    assert content.index("--- Page 2 ---") < content.index("第二页内容")
    assert doc.metadata["page_count"] == 2


def test_parse_pdf_unicode(tmp_path: Path) -> None:
    def builder(doc) -> None:
        page = doc.new_page()
        page.insert_textbox(
            pymupdf.Rect(72, 72, 500, 200), "中文内容测试", fontname="china-s"
        )

    path = _save(tmp_path / "unicode.pdf", builder)
    doc = PdfParser().parse(path)

    assert "中文内容测试" in doc.content
    assert doc.metadata["has_text"] is True


def test_parse_pdf_empty(tmp_path: Path) -> None:
    path = _save(tmp_path / "empty.pdf", lambda doc: doc.new_page())
    doc = PdfParser().parse(path)

    assert doc.format == "pdf"
    assert doc.content == ""
    assert doc.metadata["has_text"] is False
    assert doc.metadata["page_count"] == 1


def test_parse_pdf_table(tmp_path: Path) -> None:
    def builder(doc) -> None:
        page = doc.new_page()
        _add_table(
            page,
            pymupdf.Rect(72, 72, 320, 160),
            [["姓名", "年龄"], ["张三", "20"]],
        )

    path = _save(tmp_path / "table.pdf", builder)
    doc = PdfParser().parse(path)

    assert "|姓名|年龄|" in doc.content
    assert "|---|---|" in doc.content
    assert "|张三|20|" in doc.content
    assert doc.metadata["table_count"] == 1
    # 单元格文本只出现在 Markdown 表格内，不作为独立纯文本行重复输出
    lines = [line.strip() for line in doc.content.split("\n")]
    assert "姓名" not in lines
    assert "张三" not in lines


def test_parse_pdf_metadata(tmp_path: Path) -> None:
    def builder(doc) -> None:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(72, 72, 500, 200), "内容")
        doc.set_metadata(
            {
                "title": "虚构标题",
                "author": "虚构作者",
                "creationDate": "D:20240102030405+00'00'",
                "modDate": "D:20240607080910+00'00'",
            }
        )

    path = _save(tmp_path / "meta.pdf", builder)
    doc = PdfParser().parse(path)

    assert doc.metadata["parser_name"] == "pdf"
    assert doc.metadata["parser_version"] == "0.2.0"
    assert doc.metadata["page_count"] == 1
    assert doc.metadata["has_text"] is True
    assert doc.metadata["table_count"] == 0
    assert doc.metadata["title"] == "虚构标题"
    assert doc.metadata["author"] == "虚构作者"
    assert doc.metadata["created_at"] == "2024-01-02T03:04:05"
    assert doc.metadata["modified_at"] == "2024-06-07T08:09:10"


def test_parse_pdf_scanned(tmp_path: Path) -> None:
    def builder(doc) -> None:
        page = doc.new_page()
        page.insert_image(pymupdf.Rect(0, 0, 200, 200), stream=_make_png())

    path = _save(tmp_path / "scanned.pdf", builder)
    doc = PdfParser().parse(path)

    assert doc.content == ""
    assert doc.metadata["has_text"] is False
    assert doc.metadata["page_count"] == 1


def test_parse_pdf_multi_column(tmp_path: Path) -> None:
    def builder(doc) -> None:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(72, 72, 250, 200), "左列上", fontname="china-s")
        page.insert_textbox(pymupdf.Rect(72, 100, 250, 200), "左列下", fontname="china-s")
        page.insert_textbox(pymupdf.Rect(320, 72, 500, 200), "右列上", fontname="china-s")
        page.insert_textbox(pymupdf.Rect(320, 100, 500, 200), "右列下", fontname="china-s")

    path = _save(tmp_path / "multi_column.pdf", builder)
    doc = PdfParser().parse(path)

    content = doc.content
    # 阅读顺序：左列上 → 右列上 → 左列下 → 右列下（按行，非按列）
    assert content.index("左列上") < content.index("右列上")
    assert content.index("右列上") < content.index("左列下")
    assert content.index("左列下") < content.index("右列下")


def test_parse_pdf_corrupted(tmp_path: Path) -> None:
    path = tmp_path / "corrupted.pdf"
    path.write_bytes(b"not a real pdf")

    with pytest.raises(InvalidDocumentError):
        PdfParser().parse(path)


def test_parse_pdf_encrypted(tmp_path: Path) -> None:
    def builder(doc) -> None:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(72, 72, 500, 200), "secret content")

    path = tmp_path / "encrypted.pdf"
    doc = pymupdf.open()
    builder(doc)
    doc.save(
        str(path),
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="pw",
        user_pw="pw",
    )
    doc.close()

    with pytest.raises(PasswordProtectedError):
        PdfParser().parse(path)


def test_parse_pdf_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileReadError):
        PdfParser().parse(tmp_path / "missing.pdf")
