# 论文查重课程作业

陈昱绰 · 3123004519 · Python 3.9+

[作业要求](https://edu.cnblogs.com/campus/gdgy/Class78-Grade2024-CS/homework/15702)

代码、测试和报告都在 **3123004519** 目录。程序用相邻两个字符的词频向量计算余弦相似度，只依赖 Python 标准库。

## 运行

```bash
cd 3123004519
python -m pip install -r requirements.txt
python main.py "/绝对路径/原文.txt" "/绝对路径/对照.txt" "/绝对路径/答案.txt"
```

Windows 示例：

```powershell
python main.py "D:\texts\orig.txt" "D:\texts\copy.txt" "D:\texts\answer.txt"
```

答案格式如 `0.67`，保留两位小数，末尾换行。程序也在终端输出同一分数。参数错误退出码为 2，输入或输出错误为 1，成功为 0。

支持 UTF-8（含 BOM）、有 BOM 的 UTF-16、GB18030。答案不能覆盖输入文件或其硬链接。程序不联网，不加载词典，不生成业务日志或字节码缓存。参数解析、文字归一化、相似度和文件操作分别位于 `main.py`、`papercheck/similarity.py`、`papercheck/text_io.py`，流程由 `papercheck/service.py` 串联。

课堂下载包中四个 `.txt` 实际为 GitHub 源码网页，程序会从正文单元格提取文字，避免混入导航信息。无法提取正文的网页给出错误。普通论文建议使用纯文本。

## 验证

以下是开发工具，运行作业程序不需要安装它们。仓库根目录执行：

```bash
python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
python 3123004519/tools/check.py
python 3123004519/tools/measure.py
python 3123004519/tools/draw_reports.py
```

测试覆盖计算结果、编码、路径、异常及真正的命令行调用；报告在 `3123004519/reports/`。性能比较保留首版 `tools/baseline.py` 和 `tools/baseline_io.py`，采用相同输入交替运行五次的中位数。`tracemalloc` 表示 Python 分配峰值，不代表整个进程内存。

若要复现课堂样例结果，请自行解压课堂提供的“测试文本.zip”，把六个文件直接放在 `3123004519/samples/official/`。该目录已忽略，公共仓库只保存文件校验值和运行结果，不包含小说全文。没有课堂样例也能运行全部单元测试和合成性能比较。

本程序衡量字面相似度，不能识别所有同义改写，也不能替代人工判定。开发和文档使用 AI 辅助；PSP 记录注明实际执行口径。

## 文章与结果

- [博客正文](3123004519/docs/博客正文.md)、[博客园粘贴版](3123004519/docs/博客园草稿.md)
- [测试记录](3123004519/reports/tests.txt)、[覆盖率](3123004519/reports/coverage.txt)
- [性能原始数据](3123004519/reports/performance.json)、[完整进程内存](3123004519/reports/memory.json)
- [GitHub Actions](https://github.com/Cy3807/SchoolWork-PaperSimilarity/actions)：Windows/Linux，Python 3.9/3.12

辅助开发环境以 `requirements-dev.txt` 为准；`tools/memory_probe.py` 是 macOS 的补充内存测量工具。课堂样例不在公共仓库，校验值记录在 `reports/sample-manifest.json`。
