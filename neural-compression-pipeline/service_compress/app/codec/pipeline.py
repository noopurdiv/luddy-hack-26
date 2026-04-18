"""Lossless pipeline: BWT → MTF → canonical Huffman (frequency-adaptive per message).

Uses only this repository's Huffman implementation — no zlib/gzip/DEFLATE (per case rules).
"""

from __future__ import annotations

import base64

from app.codec.bwt import bwt_decode, bwt_encode, mtf_decode, mtf_encode
from app.codec.huffman import analyze_byte_source_for_huffman, huffman_compress, huffman_decompress


def compress(text: str) -> dict:
    """
    Lossless compression: BWT clusters repeated chars, MTF converts clusters to
    small integers, then Huffman builds an optimal prefix code **adapted to that
    message's symbol frequencies** (canonical Huffman; tree derived per payload).
    """
    bwt_out, bwt_index = bwt_encode(text)
    mtf_ranks = mtf_encode(bwt_out)  # list[int], each value 0-255
    mtf_bytes = bytes(mtf_ranks)

    stats = analyze_byte_source_for_huffman(mtf_bytes)
    compressed_bytes = huffman_compress(mtf_bytes)

    original_size = len(text.encode("utf-8"))
    compressed_size = len(compressed_bytes)
    compression_rate = (
        round((1 - compressed_size / original_size) * 100, 1)
        if original_size
        else 0.0
    )

    return {
        "compressed_b64": base64.b64encode(compressed_bytes).decode("ascii"),
        "bwt_index": bwt_index,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "compression_rate": compression_rate,
        "entropy_bits_per_symbol": stats["entropy_bits_per_symbol"],
        "avg_huffman_bits_per_symbol": stats["avg_huffman_bits_per_symbol"],
        "encoding_efficiency": stats["encoding_efficiency"],
    }


def decompress(compressed_b64: str, bwt_index: int) -> str:
    """Inverse of :func:`compress`; returns the exact original text."""
    compressed_bytes = base64.b64decode(compressed_b64.encode("ascii"))
    mtf_bytes = huffman_decompress(compressed_bytes)  # bytes
    bwt_out = mtf_decode(list(mtf_bytes))  # str
    return bwt_decode(bwt_out, bwt_index)
