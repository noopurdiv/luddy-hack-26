"""Character-level accuracy helpers for OCR evaluation (pred vs reference text)."""

from __future__ import annotations


def levenshtein_distance(a: str, b: str) -> int:
    """Classic Levenshtein edit distance (insert/delete/substitute)."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            ins = prev[j + 1] + 1
            delete = cur[j] + 1
            sub = prev[j] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def character_accuracy_ratio(predicted: str, reference: str) -> float:
    """
    Normalized character accuracy from edit distance:

        1 - distance(pred, ref) / max(len(pred), len(ref), 1)

    Returns a value in [0, 1]. Empty vs empty => 1.0.
    """
    pred = predicted or ""
    ref = reference or ""
    if not pred and not ref:
        return 1.0
    dist = levenshtein_distance(pred, ref)
    denom = max(len(pred), len(ref), 1)
    return max(0.0, min(1.0, 1.0 - dist / denom))
