"""Parser 模块异常层次。"""


class ParserError(Exception):
    """解析器错误基类。"""


class UnknownFormatError(ParserError):
    """扩展名未注册到任何 parser。"""


class FileReadError(ParserError):
    """文件不存在或无法读取。"""


class DecodeError(ParserError):
    """文件解码失败（非 UTF-8）。"""
