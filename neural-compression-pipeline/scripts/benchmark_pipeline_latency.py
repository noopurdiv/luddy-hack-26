#!/usr/bin/env python3
"""
Rough end-to-end latency benchmark (graduate README requirement).

Requires services running (e.g. ``docker compose up``) and a sample PNG path.

Usage::

    python scripts/benchmark_pipeline_latency.py path/to/sample.png
    python scripts/benchmark_pipeline_latency.py path/to/sample.png "hello world text"
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import httpx

DEFAULT_OCR = "http://localhost:8001/ocr"
DEFAULT_COMPRESS = "http://localhost:8002/compress"
DEFAULT_DECOMPRESS = "http://localhost:8002/decompress"


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark OCR + compress + decompress latency.")
    parser.add_argument("image", type=Path, help="PNG/JPEG file for OCR")
    parser.add_argument(
        "fallback_text",
        nargs="?",
        default=None,
        help="If OCR returns empty, use this text for compress/decompress timings",
    )
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--ocr-url", default=DEFAULT_OCR)
    parser.add_argument("--compress-url", default=DEFAULT_COMPRESS)
    parser.add_argument("--decompress-url", default=DEFAULT_DECOMPRESS)
    args = parser.parse_args()

    if not args.image.is_file():
        print(f"File not found: {args.image}", file=sys.stderr)
        return 1

    ocr_times: list[float] = []
    cmp_times: list[float] = []
    dec_times: list[float] = []

    text_for_compress = args.fallback_text

    image_bytes = args.image.read_bytes()

    with httpx.Client(timeout=120.0) as client:
        for _ in range(args.runs):
            t0 = time.perf_counter()
            r = client.post(
                args.ocr_url,
                files={"image": (args.image.name, image_bytes)},
            )
            ocr_times.append(time.perf_counter() - t0)
            if r.status_code != 200:
                print(f"OCR HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
                break
            data = r.json()
            if data.get("text", "").strip():
                text_for_compress = data["text"]

        if not (text_for_compress or "").strip():
            print(
                "OCR returned no text and no fallback_text provided; "
                "cannot benchmark compress/decompress.",
                file=sys.stderr,
            )
            return 1

        body_text = text_for_compress.strip()

        for _ in range(args.runs):
            t0 = time.perf_counter()
            cr = client.post(args.compress_url, json={"text": body_text})
            cmp_times.append(time.perf_counter() - t0)
            if cr.status_code != 200:
                print(f"Compress HTTP {cr.status_code}", file=sys.stderr)
                return 1
            packed = cr.json()

            t1 = time.perf_counter()
            dr = client.post(
                args.decompress_url,
                json={
                    "compressed_b64": packed["compressed_b64"],
                    "bwt_index": packed["bwt_index"],
                },
            )
            dec_times.append(time.perf_counter() - t1)
            if dr.status_code != 200:
                print(f"Decompress HTTP {dr.status_code}", file=sys.stderr)
                return 1

    def summary(name: str, xs: list[float]) -> None:
        if not xs:
            return
        ms = [x * 1000 for x in xs]
        print(f"{name}: mean={statistics.mean(ms):.1f} ms  stdev={statistics.pstdev(ms):.1f} ms  (n={len(ms)})")

    summary("OCR", ocr_times)
    summary("Compress", cmp_times)
    summary("Decompress", dec_times)
    if ocr_times and cmp_times and dec_times:
        e2e = [a + b + c for a, b, c in zip(ocr_times, cmp_times, dec_times)]
        summary("Sum OCR+Compress+Decompress", e2e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
