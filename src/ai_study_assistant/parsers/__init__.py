"""Parsers 公共入口：内置 markdown/text 注册与便捷函数。"""

from pathlib import Path

from .document import Document
from .docx_parser import DocxParser
from .errors import DecodeError, FileReadError, ParserError, UnknownFormatError
from .markdown import MarkdownParser
from .pdf_parser import PdfParser
from .pptx_parser import PptxParser
from .registry import Parser, ParserRegistry
from .text import TextParser

__all__ = [
    "DecodeError",
    "Document",
    "FileReadError",
    "Parser",
    "ParserError",
    "ParserRegistry",
    "UnknownFormatError",
    "default_registry",
    "parse_file",
]

default_registry = ParserRegistry()
default_registry.register("markdown", MarkdownParser(), {".md", ".markdown"})
default_registry.register("text", TextParser(), {".txt"})
default_registry.register("docx", DocxParser(), {".docx"})
default_registry.register("pdf", PdfParser(), {".pdf"})
default_registry.register("pptx", PptxParser(), {".pptx"})


def parse_file(path: str | Path) -> Document:
    """使用默认注册表解析文件路径。"""
    return default_registry.parse(Path(path))
