"""环境冒烟测试：验证项目包可导入、测试环境可用。

注意：本文件属于测试脚手架，不是业务代码。
"""

import importlib


def test_package_importable():
    """主包可导入，证明 src 布局 + 可编辑安装正确。"""
    pkg = importlib.import_module("ai_study_assistant")
    assert pkg is not None


def test_reserved_subpackages_exist():
    """验证 Phase 0 预留的五个接口包已就位。"""
    for name in ["config", "parsers", "llm", "pipeline", "storage"]:
        importlib.import_module(f"ai_study_assistant.{name}")
