"""
Huffman compression layer — delegates to the adaptive Huffman implementation.

Exposes the same ``huffman_compress`` / ``huffman_decompress`` /
``analyze_byte_source_for_huffman`` surface consumed by pipeline.py.

No third-party compression libraries are used.  The underlying algorithm
is a from-scratch adaptive Huffman codec (see adaptive_huffman.py).
"""
from __future__ import annotations

from app.codec.adaptive_huffman import (
    adaptive_compress,
    adaptive_decompress,
    analyze_compression_metrics,
)

_FLAG_RAW = b"\x00"         # payload stored verbatim (adaptive would expand)
_FLAG_ADAPTIVE = b"\x01"    # adaptive Huffman compressed stream


def analyze_byte_source_for_huffman(data: bytes) -> dict[str, float]:
    """Shannon entropy, average code length, and encoding efficiency for *data*."""
    return analyze_compression_metrics(data)


def huffman_compress(data: bytes) -> bytes:
    """
    Compress raw bytes with adaptive Huffman coding.

    Output is prefixed with a 1-byte flag:
      ``0x00`` — raw bytes stored verbatim (adaptive Huffman would expand).
      ``0x01`` — adaptive Huffman compressed stream.
    """
    if not data:
        raise ValueError("Cannot compress empty data")
    compressed = adaptive_compress(data)
    if len(compressed) < len(data):
        return _FLAG_ADAPTIVE + compressed
    return _FLAG_RAW + data


def huffman_decompress(data: bytes) -> bytes:
    """Inverse of :func:`huffman_compress`; returns the original bytes."""
    if not data:
        raise ValueError("Empty Huffman payload")
    flag, payload = data[:1], data[1:]
    if flag == _FLAG_RAW:
        return payload
    return adaptive_decompress(payload)
