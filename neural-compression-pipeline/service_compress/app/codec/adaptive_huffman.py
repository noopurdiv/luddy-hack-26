"""
Adaptive Huffman coding — implemented from scratch.

Both encoder and decoder maintain an identical evolving Huffman tree that is
rebuilt after every symbol is processed.  No frequency table is transmitted
alongside the compressed stream; the decoder reconstructs the same tree by
replaying the same update sequence.

New (never-before-seen) symbols are announced with an ESCAPE code followed
by 8 raw bits for the symbol value.  This satisfies the "Adaptive Huffman"
requirement: the code assigned to each symbol changes as the corpus grows,
with no pre-scan of the full input.
"""
from __future__ import annotations

import heapq
import math


_ESCAPE: int = 256  # virtual symbol used as "new symbol follows" escape


# ---------------------------------------------------------------------------
# Bit I/O
# ---------------------------------------------------------------------------

class _BitWriter:
    __slots__ = ("_bits",)

    def __init__(self) -> None:
        self._bits: list[int] = []

    def write(self, bits: list[int]) -> None:
        self._bits.extend(bits)

    def to_bytes(self) -> bytes:
        bits = self._bits
        pad = (-len(bits)) % 8
        bits = bits + [0] * pad
        out = bytearray(len(bits) >> 3)
        for i in range(0, len(bits), 8):
            b = 0
            for j in range(8):
                b = (b << 1) | bits[i + j]
            out[i >> 3] = b
        return bytes(out)


class _BitReader:
    __slots__ = ("_data", "_pos")

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read_bit(self) -> int:
        pos = self._pos
        self._pos += 1
        byte_idx = pos >> 3
        if byte_idx >= len(self._data):
            return 0  # padding
        return (self._data[byte_idx] >> (7 - (pos & 7))) & 1


# ---------------------------------------------------------------------------
# Huffman tree builder
# ---------------------------------------------------------------------------

def _build_tree(freq: dict[int, int]) -> tuple[object, dict[int, list[int]]]:
    """
    Build a canonical min-heap Huffman tree from a frequency map.

    Returns ``(root, codes)`` where *root* is a nested-tuple tree
    (``(left, right)`` for internal nodes, ``int`` for leaves) and
    *codes* maps each symbol to its bit-list codeword.

    Tie-breaking uses sorted symbol order for determinism: given the same
    frequency table the encoder and decoder always produce the same tree.
    """
    if len(freq) == 1:
        sym = next(iter(freq))
        # 0-bit code: no bits needed for a 1-symbol alphabet.
        # Decoder hits a leaf immediately (while loop skips) → consistent.
        return sym, {sym: []}

    heap: list[tuple[int, int, object]] = []
    for i, (sym, w) in enumerate(sorted(freq.items())):
        heapq.heappush(heap, (w, i, sym))
    next_id = len(freq)

    while len(heap) > 1:
        w1, _, n1 = heapq.heappop(heap)
        w2, _, n2 = heapq.heappop(heap)
        heapq.heappush(heap, (w1 + w2, next_id, (n1, n2)))
        next_id += 1

    _, _, root = heap[0]
    codes: dict[int, list[int]] = {}

    def _walk(node: object, path: list[int]) -> None:
        if isinstance(node, int):
            codes[node] = path
        else:
            _walk(node[0], path + [0])  # type: ignore[index]
            _walk(node[1], path + [1])  # type: ignore[index]

    _walk(root, [])
    return root, codes


# ---------------------------------------------------------------------------
# Adaptive state — shared by encoder and decoder
# ---------------------------------------------------------------------------

class _AdaptiveState:
    """
    Tracks the evolving frequency table and current Huffman tree.

    After every symbol the frequency is incremented and the tree is
    rebuilt.  Encoder and decoder instantiate one each and perform the
    same updates in lock-step, so they always share the same codes.
    """

    __slots__ = ("_freq", "_root", "_codes")

    def __init__(self) -> None:
        # ESCAPE is seeded so there is always a valid code for new symbols
        self._freq: dict[int, int] = {_ESCAPE: 1}
        self._root, self._codes = _build_tree(self._freq)

    # ---- internal helpers ----

    def _rebuild(self) -> None:
        self._root, self._codes = _build_tree(self._freq)

    def _see_new(self, sym: int) -> None:
        self._freq[sym] = 1
        self._rebuild()

    def _increment(self, sym: int) -> None:
        self._freq[sym] += 1
        self._rebuild()

    # ---- encoder ----

    def encode(self, sym: int) -> list[int]:
        """Return the bit sequence to emit for *sym* and advance state."""
        if sym not in self._freq:
            # New symbol: emit ESCAPE code + 8-bit literal (MSB first)
            bits: list[int] = list(self._codes[_ESCAPE])
            for i in range(7, -1, -1):
                bits.append((sym >> i) & 1)
            self._see_new(sym)
        else:
            bits = list(self._codes[sym])
            self._increment(sym)
        return bits

    # ---- decoder ----

    def decode(self, reader: _BitReader) -> int:
        """Read bits from *reader* until one symbol is decoded; advance state."""
        node: object = self._root
        while isinstance(node, tuple):
            node = node[0] if reader.read_bit() == 0 else node[1]  # type: ignore[index]
        sym: int = node  # type: ignore[assignment]

        if sym == _ESCAPE:
            # Read the 8-bit literal that follows
            val = 0
            for _ in range(8):
                val = (val << 1) | reader.read_bit()
            self._see_new(val)
            return val
        else:
            self._increment(sym)
            return sym


# ---------------------------------------------------------------------------
# Public compression / decompression API
# ---------------------------------------------------------------------------

def adaptive_compress(data: bytes) -> bytes:
    """
    Compress *data* with adaptive Huffman coding.

    Stream format: 4-byte big-endian symbol count followed by the packed
    bit stream.  No frequency table header is stored — the decoder
    reconstructs the identical tree by replaying the same updates.
    """
    if not data:
        raise ValueError("Cannot compress empty data")
    state = _AdaptiveState()
    writer = _BitWriter()
    for sym in data:
        writer.write(state.encode(sym))
    return len(data).to_bytes(4, "big") + writer.to_bytes()


def adaptive_decompress(data: bytes) -> bytes:
    """Inverse of :func:`adaptive_compress`; returns the exact original bytes."""
    if len(data) < 4:
        raise ValueError("Truncated adaptive Huffman stream")
    n = int.from_bytes(data[:4], "big")
    reader = _BitReader(data[4:])
    state = _AdaptiveState()
    out = bytearray(n)
    for i in range(n):
        out[i] = state.decode(reader)
    return bytes(out)


# ---------------------------------------------------------------------------
# Metrics helper
# ---------------------------------------------------------------------------

def analyze_compression_metrics(data: bytes) -> dict[str, float]:
    """
    Compute Shannon entropy, average Huffman code length, and encoding
    efficiency for *data* (used for API response metrics).
    """
    n = len(data)
    if n == 0:
        return {
            "entropy_bits_per_symbol": 0.0,
            "avg_huffman_bits_per_symbol": 0.0,
            "encoding_efficiency": 1.0,
        }

    freq: dict[int, int] = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1

    h = 0.0
    for c in freq.values():
        p = c / n
        h -= p * math.log2(p)

    # One-shot Huffman tree over the empirical distribution for avg-length metric
    _, codes = _build_tree(freq)
    avg_len = sum(freq[s] * len(codes[s]) for s in freq) / n
    efficiency = (h / avg_len) if avg_len > 0 else 1.0

    return {
        "entropy_bits_per_symbol": round(h, 8),
        "avg_huffman_bits_per_symbol": round(avg_len, 8),
        "encoding_efficiency": round(efficiency, 8),
    }
