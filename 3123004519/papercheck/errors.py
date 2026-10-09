"""可预期错误的分类，供命令行统一提示。"""


class PaperError(Exception):
    """论文比较程序的业务错误。"""


class ArgumentError(PaperError):
    """参数数量不正确。"""


class InputFileError(PaperError):
    """输入文件无法读取或网页中没有正文。"""


class TextEncodingError(InputFileError):
    """输入无法按支持的编码解码。"""


class EmptyTextError(PaperError):
    """清洗后没有可比较的文字。"""


class OutputFileError(PaperError):
    """答案无法写入或会覆盖原文。"""
