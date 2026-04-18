"""Burrows–Wheeler Transform with ``$`` sentinel + optional Move-To-Front coding."""

from __future__ import annotations


_SENTINEL = "\x00"


def bwt_encode(text: str) -> tuple[str, int]:
    """
    Encode ``text`` using the BWT with a null-byte sentinel.

    Returns ``(transformed_last_column, original_row_index)``.
    """
    if _SENTINEL in text:
        raise ValueError("Input must not contain the BWT sentinel character (null byte)")
    s = text + _SENTINEL
    n = len(s)
    rotations = [s[i:] + s[:i] for i in range(n)]
    sorted_rows = sorted(rotations)
    transformed = "".join(row[-1] for row in sorted_rows)
    idx = sorted_rows.index(s)
    return transformed, idx


def bwt_decode(transformed: str, index: int) -> str:
    """
    Inverse BWT: recover the original string (without the trailing ``$``).

    Uses the classic inverse by iteratively prepending ``transformed`` and sorting.
    """
    n = len(transformed)
    if not 0 <= index < n:
        raise ValueError("index out of range for transformed string")

    table = [""] * n
    for _ in range(n):
        table = sorted(transformed[i] + table[i] for i in range(n))
    row = table[index]
    if not row.endswith(_SENTINEL):
        raise ValueError("Decoded row does not end with sentinel")
    return row[:-1]


def mtf_encode(bwt_output: str) -> list[int]:
    """
    Move-To-Front over the byte representation of ``bwt_output`` (UTF-8).

    The alphabet is bytes 0..255; ranks are integers in ``0..255`` after each step.
    This makes ``mtf_decode`` self-contained without a separate alphabet side channel.
    """
    symbols: list[int] = list(range(256))
    out: list[int] = []
    for byte in bwt_output.encode("utf-8"):
        idx = symbols.index(byte)
        out.append(idx)
        symbols.pop(idx)
        symbols.insert(0, byte)
    return out


def mtf_decode(mtf_output: list[int]) -> str:
    """Inverse MTF for UTF-8 bytes (see :func:`mtf_encode`)."""
    symbols: list[int] = list(range(256))
    buf = bytearray()
    for idx in mtf_output:
        byte = symbols[idx]
        buf.append(byte)
        symbols.pop(idx)
        symbols.insert(0, byte)
    return buf.decode("utf-8")
