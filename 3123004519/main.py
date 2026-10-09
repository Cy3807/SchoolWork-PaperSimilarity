"""用法：python main.py 原文路径 对照文路径 答案路径。"""

import sys
from pathlib import Path


def main(argv=None) -> int:
    # 在导入本地模块前关闭字节码缓存，评测运行不生成额外文件。
    sys.dont_write_bytecode = True
    from papercheck.errors import ArgumentError, PaperError
    from papercheck.service import compare_files

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    arguments = sys.argv[1:] if argv is None else argv
    try:
        if len(arguments) != 3:
            raise ArgumentError("用法：python main.py 原文路径 对照文路径 答案路径")
        score = compare_files(*(Path(argument) for argument in arguments))
    except PaperError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2 if isinstance(error, ArgumentError) else 1
    print(f"{score:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
