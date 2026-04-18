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


def test_compression_reports_entropy_metrics() -> None:
    original = "a" * 2000
    packed = compress(original)
    assert isinstance(packed.get("entropy_bits_per_symbol"), (int, float))
    assert isinstance(packed.get("avg_huffman_bits_per_symbol"), (int, float))
    assert isinstance(packed.get("encoding_efficiency"), (int, float))
    assert packed["entropy_bits_per_symbol"] >= 0
    assert packed["compression_rate"] > 0


def test_compression_reasonable_ratio_on_repetitive_input() -> None:
    original = "a" * 2000
    packed = compress(original)
    assert packed["compression_rate"] > 20.0
