"""首版：字符二元片段词频与余弦相似度。"""

import math
import unicodedata
from collections import Counter

from papercheck.errors import EmptyTextError


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    result = "".join(character for character in folded if character.isalnum())
    if not result:
        raise EmptyTextError("文本清洗后没有有效文字")
    return result


def count_features(text: str, width: int) -> Counter:
    features = [text[index : index + width] for index in range(len(text) - width + 1)]
    return Counter(features)


def cosine(left: Counter, right: Counter) -> float:
    keys = set(left) | set(right)
    vector_left = [left.get(key, 0) for key in keys]
    vector_right = [right.get(key, 0) for key in keys]
    dot = sum(a * b for a, b in zip(vector_left, vector_right))
    norm_left = math.sqrt(sum(value * value for value in vector_left))
    norm_right = math.sqrt(sum(value * value for value in vector_right))
    return min(1.0, max(0.0, dot / (norm_left * norm_right)))


def similarity(original: str, candidate: str) -> float:
    left, right = normalize(original), normalize(candidate)
    if left == right:
        return 1.0
    width = 1 if min(len(left), len(right)) < 2 else 2
    return cosine(count_features(left, width), count_features(right, width))
