"""计算、输入输出、异常及真实命令行测试。"""

import contextlib
import io
import json
import math
import os
import random
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import main
from papercheck.errors import (
    EmptyTextError,
    InputFileError,
    OutputFileError,
    TextEncodingError,
)
from papercheck.service import compare_files
from papercheck.similarity import cosine, count_features, normalize, similarity
from papercheck.text_io import (
    SourcePageParser,
    decode_text,
    read_paper,
    unwrap_source_page,
    validate_output,
    write_answer,
)

ROOT = Path(__file__).resolve().parents[1]


class CalculationTests(unittest.TestCase):
    def test_identical_text(self):
        self.assertEqual(similarity("论文查重算法", "论文查重算法"), 1.0)

    def test_normalization_equivalence(self):
        self.assertEqual(similarity("ＡＢＣ １２３，中文！", "abc123中文"), 1.0)

    def test_casefold_and_combining_characters(self):
        self.assertEqual(normalize("Straße E\u0301"), normalize("STRASSE É"))

    def test_assignment_example(self):
        score = similarity(
            "今天是星期天，天气晴，今天晚上我要去看电影。",
            "今天是周天，天气晴朗，我晚上要去看电影。",
        )
        self.assertGreater(score, 0.5)
        self.assertLess(score, 1.0)

    def test_known_bigram_result(self):
        self.assertAlmostEqual(similarity("abcd", "abce"), 2 / 3)

    def test_completely_different(self):
        self.assertEqual(similarity("甲乙丙丁", "abcd"), 0.0)

    def test_single_character_identical(self):
        self.assertEqual(similarity("甲", "甲"), 1.0)

    def test_single_character_fallback(self):
        self.assertAlmostEqual(similarity("a", "ab"), 1 / math.sqrt(2))

    def test_deletion(self):
        self.assertAlmostEqual(similarity("abcde", "abcd"), math.sqrt(3) / 2)

    def test_empty_text_rejected(self):
        for text in ("", " \n\t", "，。！？", "\u200b"):
            with self.subTest(text=text), self.assertRaises(EmptyTextError):
                similarity(text, "正文")

    def test_feature_frequencies(self):
        self.assertEqual(count_features("ababa", 2), Counter({"ab": 2, "ba": 2}))

    def test_cosine_known_frequencies(self):
        self.assertAlmostEqual(cosine(Counter(ab=2, bc=1), Counter(ab=1, cd=2)), 0.4)

    def test_cosine_empty_vectors(self):
        for left, right in ((Counter(), Counter(a=1)), (Counter(a=0), Counter(a=1))):
            with self.assertRaises(EmptyTextError):
                cosine(left, right)

    def test_cosine_smaller_vector_either_side(self):
        a, b = Counter(a=1, b=2, c=3), Counter(a=2)
        self.assertAlmostEqual(cosine(a, b), cosine(b, a))

    def test_symmetry_and_bounds_multiple_inputs(self):
        rng = random.Random(15702)
        for _ in range(30):
            a = "".join(rng.choices("甲乙丙丁abcdef", k=rng.randint(1, 80)))
            b = "".join(rng.choices("甲乙丙丁abcdef", k=rng.randint(1, 80)))
            score = similarity(a, b)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)
            self.assertAlmostEqual(score, similarity(b, a))


class DecodingTests(unittest.TestCase):
    def test_utf8_bom(self):
        self.assertEqual(decode_text("中文".encode("utf-8-sig")), "中文")

    def test_utf16_bom(self):
        self.assertEqual(decode_text("中文".encode("utf-16")), "中文")

    def test_gb18030(self):
        self.assertEqual(decode_text("中文正文".encode("gb18030")), "中文正文")

    def test_invalid_encoding(self):
        with self.assertRaises(TextEncodingError):
            decode_text(b"\xff")

    def test_incomplete_utf16(self):
        with self.assertRaises(TextEncodingError):
            decode_text(b"\xff\xfe\x00")

    def test_plain_text_not_treated_as_html(self):
        self.assertEqual(unwrap_source_page("正文里有 <td> 标记"), "正文里有 <td> 标记")

    def test_legacy_source_page(self):
        page = (
            '<!DOCTYPE html><nav>导航不计入</nav><table><td class="blob-num">1</td>'
            '<td class="blob-code"><span>今天</span>&amp;A<br>好</td>'
            '<td class="blob-num">2</td><td class="blob-code blob-code-inner">次行</td>'
            "</table><footer>页脚不计入</footer>"
        )
        self.assertEqual(unwrap_source_page(page), "今天&A\n好\n次行")

    def test_modern_source_page(self):
        lines = ["第一行", '第二行有"引号"']
        page = "<html><script>" + json.dumps({"rawLines": lines}) + "</script></html>"
        self.assertEqual(unwrap_source_page(page), "\n".join(lines))

    def test_incomplete_code_cell(self):
        with self.assertRaises(InputFileError):
            unwrap_source_page('<html><td class="blob-code">未结束')

    def test_missing_webpage_body(self):
        for text in (
            "<html>没有正文</html>",
            '<html>"rawLines": 42</html>',
            '<html>"rawLines": [1]</html>',
            '<html>"rawLines": [',
        ):
            with self.subTest(text=text), self.assertRaises(InputFileError):
                unwrap_source_page(text)

    def test_parser_ignores_noncode_cells(self):
        parser = SourcePageParser()
        parser.feed('<div>菜单</div><td class>无类名</td><td class="blob-num">1</td>')
        self.assertEqual(parser.lines, [])


class FileFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="paper files ")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.original = self.directory / "原文.txt"
        self.candidate = self.directory / "对照.txt"
        self.answer = self.directory / "答案.txt"
        self.original.write_text("abcd", encoding="utf-8")
        self.candidate.write_text("abce", encoding="utf-8")


class FileTests(FileFixture):
    def test_compare_files_and_two_decimal_answer(self):
        self.assertAlmostEqual(compare_files(self.original, self.candidate, self.answer), 2 / 3)
        self.assertEqual(self.answer.read_text(encoding="utf-8"), "0.67\n")

    def test_missing_input(self):
        with self.assertRaises(InputFileError):
            read_paper(self.directory / "missing.txt")

    def test_directory_input(self):
        with self.assertRaises(InputFileError):
            read_paper(self.directory)

    def test_unreadable_input(self):
        with (
            patch.object(Path, "read_bytes", side_effect=PermissionError),
            self.assertRaises(InputFileError),
        ):
            read_paper(self.original)

    def test_missing_output_directory(self):
        with self.assertRaises(OutputFileError):
            write_answer(self.directory / "missing" / "answer.txt", 0.5)

    def test_unwritable_output(self):
        with (
            patch.object(Path, "write_text", side_effect=PermissionError),
            self.assertRaises(OutputFileError),
        ):
            write_answer(self.answer, 0.5)

    def test_directory_output(self):
        with self.assertRaises(OutputFileError):
            write_answer(self.directory, 0.5)

    def test_input_overwrite_rejected(self):
        before = self.original.read_bytes()
        with self.assertRaises(OutputFileError):
            compare_files(self.original, self.candidate, self.original)
        self.assertEqual(self.original.read_bytes(), before)

    def test_hardlink_alias_rejected(self):
        os.link(self.original, self.answer)
        with self.assertRaises(OutputFileError):
            compare_files(self.original, self.candidate, self.answer)

    def test_path_validation_error(self):
        with patch.object(Path, "resolve", side_effect=OSError), self.assertRaises(OutputFileError):
            validate_output(self.answer, (self.original,))

    def test_existing_answer_can_be_updated(self):
        self.answer.write_text("old", encoding="utf-8")
        compare_files(self.original, self.candidate, self.answer)
        self.assertEqual(self.answer.read_text(encoding="utf-8"), "0.67\n")

    def test_invalid_input_preserves_answer(self):
        self.answer.write_text("old", encoding="utf-8")
        self.candidate.write_text("！？", encoding="utf-8")
        with self.assertRaises(EmptyTextError):
            compare_files(self.original, self.candidate, self.answer)
        self.assertEqual(self.answer.read_text(encoding="utf-8"), "old")


class CommandLineTests(FileFixture):
    def run_command(self, arguments, **kwargs):
        return subprocess.run(
            [sys.executable, str(ROOT / "main.py"), *map(str, arguments)],
            cwd=self.directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
            **kwargs,
        )

    def test_cli_absolute_paths_with_spaces(self):
        result = self.run_command((self.original, self.candidate, self.answer))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "0.67")

    def test_cli_missing_arguments(self):
        result = self.run_command(())
        self.assertEqual(result.returncode, 2)
        self.assertIn("用法", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_missing_file(self):
        result = self.run_command((self.directory / "missing", self.candidate, self.answer))
        self.assertEqual(result.returncode, 1)
        self.assertIn("无法读取", result.stderr)

    def test_ascii_environment_error_message(self):
        result = self.run_command((), env={**os.environ, "PYTHONIOENCODING": "ascii"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("用法", result.stderr)

    def test_main_directly_success_and_failures(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(
                main.main([str(self.original), str(self.candidate), str(self.answer)]), 0
            )
            self.assertEqual(main.main([]), 2)
            self.assertEqual(main.main(["missing", str(self.candidate), str(self.answer)]), 1)

    def test_script_entrypoint(self):
        with (
            patch.object(sys, "argv", ["main.py"]),
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
        self.assertEqual(caught.exception.code, 2)

    def test_no_extra_runtime_files_or_caches(self):
        code = self.directory / "program"
        code.mkdir()
        shutil.copy2(ROOT / "main.py", code / "main.py")
        shutil.copytree(
            ROOT / "papercheck", code / "papercheck", ignore=shutil.ignore_patterns("__pycache__")
        )
        before = {p.relative_to(self.directory) for p in self.directory.rglob("*") if p.is_file()}
        result = subprocess.run(
            [
                sys.executable,
                str(code / "main.py"),
                str(self.original),
                str(self.candidate),
                str(self.answer),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {p.relative_to(self.directory) for p in self.directory.rglob("*") if p.is_file()}
        self.assertEqual(after - before, {self.answer.relative_to(self.directory)})


if __name__ == "__main__":
    unittest.main(verbosity=2)
