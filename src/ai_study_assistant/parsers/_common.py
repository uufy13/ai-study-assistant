"""解析器共享工具：文本规范化、Markdown 表格、ZIP 预检。

私有模块（下划线前缀），仅供 parsers 包内部使用，不属于公开 API。
三个二进制格式 Parser 共享同一套规范化逻辑，避免输出格式不一致与重复代码。
"""

from __future__ import annotations

import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

from .errors import InvalidDocumentError, PasswordProtectedError


def normalize_text(text: str) -> str:
    """统一换行、压缩空白、NFC 归一化，返回去头尾空白的字符串。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def make_markdown_table(rows: list[list[str]]) -> str:
    """把二维文本矩阵转成 Markdown 表格。空矩阵返回空字符串。"""
    if not rows:
        return ""
    cleaned: list[list[str]] = []
    for row in rows:
        cleaned.append([_clean_cell(cell) for cell in row])
    ncols = max(len(row) for row in cleaned)
    for row in cleaned:
        row.extend([""] * (ncols - len(row)))
    header = cleaned[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * ncols) + " |",
    ]
    for row in cleaned[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def iso_datetime(value: object) -> str | None:
    """把 datetime 对象转成 ISO-8601 字符串；空值返回 None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def check_ooxml_zip(path: Path, label: str) -> None:
    """预检 OOXML 容器（.docx / .pptx）。

    损坏抛 ``InvalidDocumentError``，加密抛 ``PasswordProtectedError``。
    """
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
    except (zipfile.BadZipFile, OSError) as exc:
        raise InvalidDocumentError(f"Not a valid {label} (corrupted): {path}") from exc
    if "EncryptionInfo" in names or "EncryptedPackage" in names:
        raise PasswordProtectedError(f"{label} is password-protected: {path}")


def _clean_cell(cell: str) -> str:
    """单元格内换行转空格、转义竖线、去空白。"""
    return cell.replace("\n", " ").replace("|", "\\|").strip()
