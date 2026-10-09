"""同机同输入比较首版与改进版，另测完整命令行和 Python 分配峰值。"""

import cProfile
import hashlib
import json
import platform
import pstats
import random
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from papercheck.service import compare_files  # noqa: E402
from papercheck.similarity import similarity  # noqa: E402
from papercheck.text_io import decode_text, unwrap_source_page  # noqa: E402
from tools import baseline, baseline_io  # noqa: E402

REPORTS = ROOT / "reports"


def measure_pair(before, after, arguments, repeats=5):
    assert abs(before(*arguments) - after(*arguments)) < 1e-12
    timings = {"before": [], "after": []}
    for repeat in range(repeats):
        functions = [("before", before), ("after", after)]
        if repeat % 2:
            functions.reverse()
        for name, function in functions:
            start = time.perf_counter()
            function(*arguments)
            timings[name].append((time.perf_counter() - start) * 1000)
    results = {}
    for name, function in [("before", before), ("after", after)]:
        tracemalloc.start()
        function(*arguments)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results[name] = {
            "median_ms": statistics.median(timings[name]),
            "samples_ms": timings[name],
            "python_peak_mib": peak / 1048576,
        }
    return results


def main():
    generator = random.Random(4519)
    results = {
        "environment": {
            "python": platform.python_version(),
            "system": platform.platform(),
            "machine": platform.machine(),
        },
        "method": "5 alternating runs; median elapsed; separate tracemalloc peak",
        "synthetic": [],
    }
    alphabet = "".join(chr(0x4E00 + index) for index in range(1200))
    for length in (1000, 10000, 100000):
        text = "".join(generator.choice(alphabet) for _ in range(length))
        altered = list(text)
        for index in range(0, length, 7):
            altered[index] = generator.choice(alphabet)
        results["synthetic"].append(
            {
                "characters_each": length,
                **measure_pair(baseline.similarity, similarity, (text, "".join(altered))),
            }
        )
    official = ROOT / "samples/official"
    if official.exists():
        original = decode_text((official / "orig.txt").read_bytes())
        wrapped = decode_text((official / "orig_0.8_del.txt").read_bytes())

        def before(left, right):
            return baseline.similarity(
                baseline_io.unwrap_source_page(left), baseline_io.unwrap_source_page(right)
            )

        def after(left, right):
            return similarity(unwrap_source_page(left), unwrap_source_page(right))

        assert baseline_io.unwrap_source_page(wrapped) == unwrap_source_page(wrapped)
        results["official_wrapped_pair"] = measure_pair(before, after, (original, wrapped))
        results["official_cli"] = []
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "answer.txt"
            for path in sorted(official.glob("*.txt")):
                start = time.perf_counter()
                process = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "main.py"),
                        str(official / "orig.txt"),
                        str(path),
                        str(output),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                )
                elapsed = (time.perf_counter() - start) * 1000
                answer = output.read_text(encoding="utf-8").strip()
                assert answer == process.stdout.strip()
                results["official_cli"].append(
                    {
                        "file": path.name,
                        "answer": answer,
                        "elapsed_ms": elapsed,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
            profiler = cProfile.Profile()
            profiler.runcall(
                compare_files, official / "orig.txt", official / "orig_0.8_del.txt", output
            )
            profiler.dump_stats(str(REPORTS / "optimized.prof"))
            with (REPORTS / "profile.txt").open("w", encoding="utf-8") as stream:
                pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats(
                    "cumulative"
                ).print_stats(20)
            stats = pstats.Stats(profiler).stats
            results["profile"] = sorted(
                [
                    {
                        "function": f"{Path(filename).name}:{line} {function}",
                        "self_ms": values[2] * 1000,
                        "cumulative_ms": values[3] * 1000,
                        "calls": values[1],
                    }
                    for (filename, line, function), values in stats.items()
                    if filename.endswith(("similarity.py", "text_io.py", "service.py"))
                ],
                key=lambda item: item["cumulative_ms"],
                reverse=True,
            )
    (REPORTS / "performance.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
