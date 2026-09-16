"""Parser 模块异常层次。"""


class ParserError(Exception):
    """解析器错误基类。"""


class UnknownFormatError(ParserError):
    """扩展名未注册到任何 parser。"""


class FileReadError(ParserError):
    """文件不存在或无法读取。"""


class DecodeError(ParserError):
    """文件解码失败（非 UTF-8）。"""


class InvalidDocumentError(ParserError):
    """文档损坏或无法解析（DOCX/PDF/PPTX）。"""


class PasswordProtectedError(ParserError):
    """文档受密码保护，需要密码才能打开。"""


class UnsupportedFeatureError(ParserError):
    """遇到 v0.2.0 暂不支持的特性。"""
