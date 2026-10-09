"""连接文件操作与纯计算接口。"""

from pathlib import Path

from .similarity import similarity
from .text_io import read_paper, validate_output, write_answer


def compare_files(original: Path, candidate: Path, answer: Path) -> float:
    validate_output(answer, (original, candidate))
    original_text = read_paper(original)
    candidate_text = read_paper(candidate)
    score = similarity(original_text, candidate_text)
    write_answer(answer, score)
    return score
