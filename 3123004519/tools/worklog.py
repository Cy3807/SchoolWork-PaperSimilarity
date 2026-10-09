"""记录本次 AI 辅助开发的实际阶段时间，独立于待评测程序。"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "reports/worklog.json"
PHASES = [
    ("Estimate", "计划", 2),
    ("Analysis", "需求分析", 5),
    ("Design Spec", "设计文档", 3),
    ("Design Review", "设计复审", 2),
    ("Coding Standard", "代码规范", 1),
    ("Design", "具体设计", 3),
    ("Coding", "编码与性能改进", 8),
    ("Code Review", "代码复审", 3),
    ("Test", "测试", 6),
    ("Test Report", "测试报告", 4),
    ("Size Measurement", "工作量统计", 1),
    ("Postmortem", "总结与博客整理", 3),
]


def main():
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="microseconds")
    data = json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else {
        "actor": "AI-assisted execution, not personal student effort",
        "recording_started": now,
        "plan": [{"phase": key, "name": name, "estimate_minutes": estimate}
                 for key, name, estimate in PHASES],
        "sessions": [],
    }
    if data["sessions"] and "ended_at" not in data["sessions"][-1]:
        session = data["sessions"][-1]
        session["ended_at"] = now
        session["seconds"] = (datetime.fromisoformat(now)
                              - datetime.fromisoformat(session["started_at"])).total_seconds()
    phase = sys.argv[1]
    if phase != "stop":
        if phase not in {key for key, _, _ in PHASES}:
            raise ValueError("未知阶段")
        data["sessions"].append({"phase": phase, "started_at": now})
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(phase, now)


if __name__ == "__main__":
    main()
