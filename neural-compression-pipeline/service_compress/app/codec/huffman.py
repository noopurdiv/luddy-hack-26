"""UTF-8 Huffman compression built on Nayuki's reference ``huffmancoding`` module."""

from __future__ import annotations

import io

from app.codec.huffmancoding import (
    BitInputStream,
    BitOutputStream,
    CanonicalCode,
    FrequencyTable,
    HuffmanDecoder,
    HuffmanEncoder,
)

_SYMBOL_LIMIT = 256
_HEADER_SYMBOL_COUNT = 4
_HEADER_CODE_LENGTHS = _SYMBOL_LIMIT


def _build_frequency_table(data: bytes) -> FrequencyTable:
    freqs = [0] * _SYMBOL_LIMIT
    for b in data:
        freqs[b] += 1
    return FrequencyTable(freqs)


def huffman_compress(text: str) -> bytes:
    """
    Compress UTF-8 text with Huffman coding.

    Header layout (big-endian):
      - 4 bytes: ``num_symbols`` — number of bytes in the original UTF-8 payload
      - 256 bytes: canonical code length per symbol ``0..255`` (0 = unused)
      - remaining bytes: Huffman-coded bit stream (zero-padded to a byte boundary)
    """
    data = text.encode("utf-8")
    if len(data) == 0:
        raise ValueError("Cannot compress empty text")

    ft = _build_frequency_table(data)
    code_tree = ft.build_code_tree()
    canon = CanonicalCode(tree=code_tree, symbollimit=_SYMBOL_LIMIT)
    lengths = canon.codelengths

    buf = io.BytesIO()
    buf.write(len(data).to_bytes(_HEADER_SYMBOL_COUNT, "big", signed=False))
    buf.write(bytes(lengths))

    bit_out = BitOutputStream(buf)
    enc = HuffmanEncoder(bit_out)
    enc.codetree = canon.to_code_tree()
    for symbol in data:
        enc.write(symbol)
    # Pad to byte boundary without closing the BytesIO so getvalue() still works.
    while bit_out.numbitsfilled != 0:
        bit_out.write(0)
    return buf.getvalue()


def huffman_decompress(data: bytes) -> str:
    """Inverse of :func:`huffman_compress`; returns the original Unicode string."""
    min_len = _HEADER_SYMBOL_COUNT + _HEADER_CODE_LENGTHS
    if len(data) < min_len:
        raise ValueError("Truncated Huffman payload")

    num_symbols = int.from_bytes(data[:_HEADER_SYMBOL_COUNT], "big", signed=False)
    lengths = list(data[_HEADER_SYMBOL_COUNT:min_len])
    payload = data[min_len:]

    if len(lengths) != _SYMBOL_LIMIT:
        raise ValueError("Invalid canonical code length table")

    canon = CanonicalCode(codelengths=lengths)
    tree = canon.to_code_tree()

    inp = io.BytesIO(payload)
    bit_in = BitInputStream(inp)
    dec = HuffmanDecoder(bit_in)
    dec.codetree = tree

    out = bytearray()
    for _ in range(num_symbols):
        out.append(dec.read())
    bit_in.close()

    return out.decode("utf-8")
