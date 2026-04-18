"""Two-stage pipeline: BWT on text, then Huffman on the BWT string."""

from __future__ import annotations

import base64

from app.codec.bwt import bwt_decode, bwt_encode
from app.codec.huffman import huffman_compress, huffman_decompress


def compress(text: str) -> dict:
    """Lossless compression: BWT followed by Huffman on UTF-8."""
    bwt_out, bwt_index = bwt_encode(text)
    compressed_bytes = huffman_compress(bwt_out)

    original_size = len(text.encode("utf-8"))
    compressed_size = len(compressed_bytes)
    ratio = round(original_size / compressed_size, 2) if compressed_size else 0.0

    return {
        "compressed_b64": base64.b64encode(compressed_bytes).decode("ascii"),
        "bwt_index": bwt_index,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "ratio": ratio,
    }


def decompress(compressed_b64: str, bwt_index: int) -> str:
    """Inverse of :func:`compress`; returns the exact original text."""
    compressed_bytes = base64.b64decode(compressed_b64.encode("ascii"))
    bwt_out = huffman_decompress(compressed_bytes)
    return bwt_decode(bwt_out, bwt_index)
