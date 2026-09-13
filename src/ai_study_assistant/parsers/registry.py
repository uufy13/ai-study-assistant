"""Parser 协议与注册表。"""

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from .document import Document
from .errors import UnknownFormatError


class Parser(Protocol):
    """解析器协议：接收文件路径，返回 Document。"""

    def parse(self, path: Path) -> Document: ...


class ParserRegistry:
    """格式名 + 扩展名列表两级映射的解析器注册表。"""

    def __init__(self) -> None:
        self._parsers: dict[str, Parser] = {}
        self._extensions: dict[str, str] = {}

    def register(self, name: str, parser: Parser, extensions: Iterable[str]) -> None:
        """以格式名注册 parser，并把一组扩展名映射到该格式名。"""
        self._parsers[name] = parser
        for ext in extensions:
            self._extensions[ext.lower()] = name

    def get(self, name: str) -> Parser:
        """按格式名取 parser。"""
        return self._parsers[name]

    def parse(self, path: Path) -> Document:
        """按扩展名路由到对应 parser 并解析。"""
        ext = path.suffix.lower()
        name = self._extensions.get(ext)
        if name is None:
            raise UnknownFormatError(f"Unsupported file extension: {ext!r}")
        parser = self._parsers[name]
        return parser.parse(path)

    def supported_extensions(self) -> set[str]:
        """返回已注册的全部扩展名。"""
        return set(self._extensions.keys())
