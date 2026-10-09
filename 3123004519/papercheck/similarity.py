"""字符二元片段词频与余弦相似度，保留稀疏频数。"""

import math
import unicodedata
from collections import Counter

from .errors import EmptyTextError


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    result = "".join(character for character in folded if character.isalnum())
    if not result:
        raise EmptyTextError("文本清洗后没有有效文字")
    return result


def count_features(text: str, width: int) -> Counter:
    return Counter(text[index : index + width] for index in range(len(text) - width + 1))


def cosine(left: Counter, right: Counter) -> float:
    norm_left = math.sqrt(sum(value * value for value in left.values()))
    norm_right = math.sqrt(sum(value * value for value in right.values()))
    denominator = norm_left * norm_right
    if denominator == 0:
        raise EmptyTextError("特征向量不能为空")
    if len(left) > len(right):
        left, right = right, left
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    return min(1.0, max(0.0, dot / denominator))


def similarity(original: str, candidate: str) -> float:
    left, right = normalize(original), normalize(candidate)
    if left == right:
        return 1.0
    width = 1 if min(len(left), len(right)) < 2 else 2
    return cosine(count_features(left, width), count_features(right, width))
