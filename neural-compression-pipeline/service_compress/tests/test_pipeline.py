from app.codec.pipeline import compress, decompress


def test_roundtrip_simple() -> None:
    original = "hello world"
    packed = compress(original)
    restored = decompress(packed["compressed_b64"], packed["bwt_index"])
    assert restored == original


def test_roundtrip_long() -> None:
    # five hundred words (space-separated)
    long_text = " ".join(["lorem"] * 500)
    packed = compress(long_text)
    restored = decompress(packed["compressed_b64"], packed["bwt_index"])
    assert restored == long_text


def test_ratio_positive() -> None:
    # Long repeated input compresses well enough to beat Huffman header overhead
    original = "a" * 2000
    packed = compress(original)
    assert packed["ratio"] > 1.0
