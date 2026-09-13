"""Parser 模块单元测试（覆盖设计文档第 7 节 12 个用例）。"""

from pathlib import Path

import pytest

from ai_study_assistant.parsers import (
    DecodeError,
    Document,
    FileReadError,
    ParserRegistry,
    UnknownFormatError,
    default_registry,
    parse_file,
)
from ai_study_assistant.parsers.markdown import MarkdownParser


class _FakeParser:
    def parse(self, path: Path) -> Document:
        return Document(source=path, format="fake", content="fake-content")


def test_parse_md(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    path.write_text("# Hello\n\nworld", encoding="utf-8")
    doc = default_registry.parse(path)
    assert doc.format == "markdown"
    assert doc.content == "# Hello\n\nworld"
    assert doc.source == path


def test_parse_txt(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("plain text", encoding="utf-8")
    doc = default_registry.parse(path)
    assert doc.format == "text"
    assert doc.content == "plain text"


def test_parse_markdown_extension(tmp_path: Path) -> None:
    path = tmp_path / "note.markdown"
    path.write_text("content", encoding="utf-8")
    doc = default_registry.parse(path)
    assert doc.format == "markdown"
    assert doc.content == "content"


def test_case_insensitive_extension(tmp_path: Path) -> None:
    path_upper = tmp_path / "note.MD"
    path_upper.write_text("md upper", encoding="utf-8")
    assert default_registry.parse(path_upper).format == "markdown"

    path_mixed = tmp_path / "note.Txt"
    path_mixed.write_text("txt mixed", encoding="utf-8")
    assert default_registry.parse(path_mixed).format == "text"


def test_unknown_extension(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    path.write_text("data", encoding="utf-8")
    with pytest.raises(UnknownFormatError):
        default_registry.parse(path)


def test_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"
    with pytest.raises(FileReadError):
        default_registry.parse(missing)


def test_utf8_bom_removed(tmp_path: Path) -> None:
    path = tmp_path / "bom.md"
    path.write_bytes("\ufeff".encode("utf-8") + b"hello")
    doc = default_registry.parse(path)
    assert doc.content == "hello"


def test_non_utf8_decode_error(tmp_path: Path) -> None:
    path = tmp_path / "gbk.txt"
    path.write_bytes("中文".encode("gbk"))
    with pytest.raises(DecodeError):
        default_registry.parse(path)


def test_registry_multiple_extensions_same_parser(tmp_path: Path) -> None:
    registry = ParserRegistry()
    parser = MarkdownParser()
    registry.register("markdown", parser, {".md", ".markdown"})
    md_path = tmp_path / "a.md"
    md_path.write_text("a", encoding="utf-8")
    markdown_path = tmp_path / "b.markdown"
    markdown_path.write_text("b", encoding="utf-8")

    assert registry.parse(md_path).format == "markdown"
    assert registry.parse(markdown_path).format == "markdown"
    assert registry.get("markdown") is parser


def test_custom_parser_registration(tmp_path: Path) -> None:
    registry = ParserRegistry()
    registry.register("fake", _FakeParser(), {".fake"})
    path = tmp_path / "x.fake"
    path.write_text("whatever", encoding="utf-8")
    doc = registry.parse(path)
    assert doc.format == "fake"
    assert doc.content == "fake-content"
    assert ".fake" in registry.supported_extensions()


def test_parse_file_helper(tmp_path: Path) -> None:
    path = tmp_path / "helper.txt"
    path.write_text("helper-content", encoding="utf-8")
    doc = parse_file(str(path))
    assert isinstance(doc, Document)
    assert doc.format == "text"
    assert doc.content == "helper-content"


def test_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")
    doc = default_registry.parse(path)
    assert doc.content == ""
    assert doc.format == "text"
