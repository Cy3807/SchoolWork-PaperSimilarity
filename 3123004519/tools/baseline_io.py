"""只读取指定输入、写入指定答案；支持课堂样例中的源码网页包装。"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

from papercheck.errors import InputFileError, OutputFileError, TextEncodingError


class SourcePageParser(HTMLParser):
    """从旧版 GitHub 源码网页的 blob-code 单元格提取正文。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.current = []
        self.capturing = False

    def handle_starttag(self, tag, attrs):
        if tag == "td" and "blob-code" in dict(attrs).get("class", "").split():
            self.capturing = True
            self.current = []
        elif tag == "br" and self.capturing:
            self.current.append("\n")

    def handle_data(self, data):
        if self.capturing:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.capturing:
            self.lines.append("".join(self.current))
            self.capturing = False


def decode_text(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")
        except UnicodeError as error:
            raise TextEncodingError("UTF-16 文本编码不完整") from error
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return raw.decode("gb18030")
        except UnicodeDecodeError as error:
            raise TextEncodingError("文件不是可读取的 UTF-8、UTF-16 或 GB18030 文本") from error


def unwrap_source_page(text: str) -> str:
    beginning = text.lstrip()[:100].lower()
    if not (beginning.startswith("<!doctype html") or beginning.startswith("<html")):
        return text
    parser = SourcePageParser()
    parser.feed(text)
    if parser.lines:
        return "\n".join(parser.lines)
    # 同时兼容新版源码网页嵌入的 JSON，不运行任何网页脚本。
    marker = re.search(r'"rawLines"\s*:', text)
    if marker:
        try:
            lines, _ = json.JSONDecoder().raw_decode(text[marker.end() :].lstrip())
        except json.JSONDecodeError as error:
            raise InputFileError("源码网页的正文数据不完整") from error
        if isinstance(lines, list) and all(isinstance(line, str) for line in lines):
            return "\n".join(lines)
    raise InputFileError("输入是网页，未找到论文正文，请使用纯文本文件")


def read_paper(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise InputFileError(f"无法读取输入文件：{path}") from error
    return unwrap_source_page(decode_text(raw))


def validate_output(output: Path, sources) -> None:
    try:
        for source in sources:
            same_path = output.resolve() == source.resolve()
            same_file = output.exists() and source.exists() and output.samefile(source)
            if same_path or same_file:
                raise OutputFileError("答案文件不能与输入文件相同")
    except (OSError, RuntimeError) as error:
        raise OutputFileError("无法检查答案文件路径") from error


def write_answer(path: Path, score: float) -> None:
    try:
        path.write_text(f"{score:.2f}\n", encoding="utf-8")
    except OSError as error:
        raise OutputFileError(f"无法写入答案文件：{path}") from error
