"""统一的 Document 输出结构。"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    """解析产物：源文件路径、格式、正文与元数据。"""

    source: Path
    format: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
