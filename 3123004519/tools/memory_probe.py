"""macOS 原生命令记录整个解释器进程的最大驻留内存。"""

import json
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    if platform.system() != "Darwin":
        print("此补充测量使用 macOS /usr/bin/time -l；其他系统请用本地等效工具。")
        return
    original = ROOT / "samples/official/orig.txt"
    candidate = ROOT / "samples/official/orig_0.8_del.txt"
    if not original.exists() or not candidate.exists():
        print("请先放入课堂样例。")
        return
    with tempfile.TemporaryDirectory() as temporary:
        command = [
            "/usr/bin/time",
            "-l",
            sys.executable,
            str(ROOT / "main.py"),
            str(original),
            str(candidate),
            str(Path(temporary) / "answer.txt"),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=True)
    match = re.search(r"(\d+)\s+maximum resident set size", result.stderr)
    if not match:
        raise RuntimeError("未找到 macOS 驻留内存测量值")
    record = {
        "tool": "/usr/bin/time -l",
        "scope": "full Python CLI process, official del pair",
        "maximum_resident_bytes": int(match[1]),
        "maximum_resident_mib": int(match[1]) / 1048576,
        "answer": result.stdout.strip(),
    }
    (ROOT / "reports/memory.txt").write_text(result.stderr, encoding="utf-8")
    (ROOT / "reports/memory.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
