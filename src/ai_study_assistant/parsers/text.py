"""纯文本文件解析器。"""

from pathlib import Path

from .document import Document
from .errors import DecodeError, FileReadError


class TextParser:
    """读取 UTF-8-SIG 文本文件，返回扁平文本 Document。"""

    def parse(self, path: Path) -> Document:
        try:
            content = path.read_text(encoding="utf-8-sig")
        except FileNotFoundError as exc:
            raise FileReadError(f"File not found: {path}") from exc
        except UnicodeDecodeError as exc:
            raise DecodeError(f"Failed to decode {path}: {exc}") from exc
        except OSError as exc:
            raise FileReadError(f"Could not read file: {path}") from exc

        return Document(
            source=path,
            format="text",
            content=content,
        )
