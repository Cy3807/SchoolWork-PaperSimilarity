"""将原始 JSON 报告画成便于博客阅读的图片，未伪装为工具截图。"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
COLORS = ["#94a3b8", "#2563eb"]
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})


def draw_performance():
    data = json.loads((REPORTS / "performance.json").read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), layout="constrained")
    sizes = [str(row["characters_each"]) for row in data["synthetic"]]
    for axis, metric, label in zip(
        axes[:2],
        ["median_ms", "python_peak_mib"],
        ["Elapsed time (ms)", "Python allocation peak (MiB)"],
    ):
        for name, color in zip(["before", "after"], COLORS):
            values = [row[name][metric] for row in data["synthetic"]]
            axis.plot(sizes, values, marker="o", color=color, linewidth=2, label=name)
            for index, value in enumerate(values):
                axis.annotate(
                    f"{value:.2f}",
                    (index, value),
                    xytext=(0, 7),
                    textcoords="offset points",
                    ha="center",
                    fontsize=9,
                )
        axis.set_yscale("log")
        axis.set_xlabel("Characters per document (log y scale)")
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.2)
        axis.legend()
    profile = [
        row
        for row in data.get("profile", [])
        if any(
            keyword in row["function"] for keyword in ["unwrap_source_page", "normalize", "cosine"]
        )
    ]
    if profile:
        names = [row["function"].split()[-1] for row in profile]
        values = [row["cumulative_ms"] for row in profile]
        axes[2].barh(names[::-1], values[::-1], color="#2563eb")
        axes[2].set_xlabel("cProfile cumulative time (ms)")
        axes[2].set_title("Official del sample: selected hotspots")
        axes[2].grid(axis="x", alpha=0.2)
    else:
        axes[2].set_visible(False)
    fig.suptitle("Measured before / after optimization - Python 3.9.6, arm64 macOS", fontsize=14)
    fig.savefig(REPORTS / "performance.png", dpi=150)
    plt.close(fig)


def draw_coverage():
    data = json.loads((REPORTS / "coverage.json").read_text(encoding="utf-8"))
    tests = json.loads((REPORTS / "tests.json").read_text(encoding="utf-8"))
    rows = []
    for filename, item in data["files"].items():
        summary = item["summary"]
        rows.append(
            [
                filename.split("3123004519/")[-1],
                f"{summary['covered_lines']}/{summary['num_statements']}",
                f"{summary['covered_branches']}/{summary['num_branches']}",
                f"{summary['percent_covered']:.1f}%",
            ]
        )
    totals = data["totals"]
    rows.append(
        [
            "TOTAL",
            f"{totals['covered_lines']}/{totals['num_statements']}",
            f"{totals['covered_branches']}/{totals['num_branches']}",
            f"{totals['percent_covered']:.1f}%",
        ]
    )
    fig, ax = plt.subplots(figsize=(11, 4.6), layout="constrained")
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=["Production module", "Statements", "Branch exits", "Coverage"],
        colWidths=[0.49, 0.17, 0.18, 0.16],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.85)
    for (row, _), cell in table.get_celld().items():
        cell.set_edgecolor("#e2e8f0")
        if row == 0:
            cell.set_facecolor("#dbeafe")
            cell.set_text_props(weight="bold")
        elif row == len(rows):
            cell.set_facecolor("#eff6ff")
    ax.set_title(
        f"coverage.py branch report | {tests['run']} tests, "
        f"{tests['failures']} failures, {tests['errors']} errors",
        fontsize=15,
        pad=20,
    )
    fig.text(
        0.5,
        0.035,
        "Generated from coverage.json; subprocess runs excluded; direct main() and runpy tested.",
        ha="center",
        fontsize=10,
        color="#475569",
    )
    fig.savefig(REPORTS / "coverage.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    draw_performance()
    draw_coverage()
