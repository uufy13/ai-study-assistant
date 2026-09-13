"""Pytest 夹具：沙箱兼容的 tmp_path。

背景：在 DSH 沙箱环境中，`tempfile.mkdtemp` 创建的目录会立即变为不可访问
（PermissionError），导致 pytest 内置的 `tmp_path` fixture 失效。
本文件仅在检测到沙箱（存在 DSH_SESSION_ID）时，提供一个基于 `Path.mkdir`
的等价实现；在正常环境则不做任何覆盖，仍使用 pytest 内置的 tmp_path。

依据：Path.mkdir 创建的目录在沙箱内可正常读写、且 shutil.rmtree 可正常清理。
"""

import os
import shutil
import uuid
from pathlib import Path

import pytest

_IN_DSH_SANDBOX = "DSH_SESSION_ID" in os.environ


if _IN_DSH_SANDBOX:

    @pytest.fixture
    def tmp_path() -> Path:
        """在沙箱内提供等价于内置 tmp_path 的临时目录（Path.mkdir 实现）。"""
        base = Path(__file__).resolve().parent.parent / ".pytest-tmp"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"test-{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)
