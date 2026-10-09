"""运行独立测试并导出原始覆盖率，不依赖课堂样例。"""

import io
import json
import sys
import unittest
from pathlib import Path

import coverage

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
sys.path.insert(0, str(ROOT))


def main():
    REPORTS.mkdir(exist_ok=True)
    measured = coverage.Coverage(
        branch=True,
        source=[str(ROOT / "papercheck"), "main"],
        data_file=str(REPORTS / ".coverage"),
        config_file=False,
    )
    measured.start()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    measured.stop()
    measured.save()
    REPORTS.joinpath("tests.txt").write_text(stream.getvalue(), encoding="utf-8")
    measured.json_report(outfile=str(REPORTS / "coverage.json"))
    measured.html_report(directory=str(REPORTS / "htmlcov"))
    summary = io.StringIO()
    measured.report(file=summary, show_missing=True)
    REPORTS.joinpath("coverage.txt").write_text(summary.getvalue(), encoding="utf-8")
    REPORTS.joinpath("tests.json").write_text(
        json.dumps(
            {
                "run": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "python": sys.version.split()[0],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(stream.getvalue())
    print(summary.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
