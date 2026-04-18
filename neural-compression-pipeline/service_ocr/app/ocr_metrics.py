"""Load stored OCR validation metrics (written by training/evaluation scripts)."""

from __future__ import annotations

import json
from pathlib import Path

_METRICS_DIR = Path(__file__).resolve().parent / "model" / "mnist-model"

# (mtime_ns, best_validation_accuracy or None) — avoid re-reading JSON every OCR request.
_recorded_val_cache: tuple[float | None, float | None] = (None, None)


def recorded_mnist_validation_accuracy() -> float | None:
    """
    Best validation split accuracy (0–1) from ``training_metrics.json`` if present.

    For MNIST digit classification this equals recorded character-level accuracy on the
    held-out validation split (see ``training/train_mnist_cnn.py``).
    """
    path = _METRICS_DIR / "training_metrics.json"
    if not path.is_file():
        return None
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return None

    global _recorded_val_cache
    if _recorded_val_cache[0] == mtime:
        return _recorded_val_cache[1]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _recorded_val_cache = (mtime, None)
        return None

    v = data.get("best_validation_accuracy")
    out: float | None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        x = float(v)
        out = x if 0.0 <= x <= 1.0 else (x / 100.0 if 0.0 < x <= 100.0 else None)
    else:
        out = None

    _recorded_val_cache = (mtime, out)
    return out


def load_ocr_accuracy_payload() -> dict:
    """
    Return MNIST CNN metrics from disk if ``training_metrics.json`` /
    ``noise_metrics.json`` exist under ``app/model/mnist-model/``.
    """
    mnist_path = _METRICS_DIR / "training_metrics.json"
    noise_path = _METRICS_DIR / "noise_metrics.json"

    mnist: dict | None = None
    noise: dict | None = None

    if mnist_path.is_file():
        try:
            mnist = json.loads(mnist_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            mnist = {"error": "could_not_read_training_metrics"}

    if noise_path.is_file():
        try:
            noise = json.loads(noise_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            noise = {"error": "could_not_read_noise_metrics"}

    available = mnist is not None or noise is not None

    hint = (
        "Run `python training/train_mnist_cnn.py` from `service_ocr/` to generate "
        "MNIST test/val accuracy. Optionally run `python training/evaluate_noise_profiles.py` "
        "for Gaussian and salt-and-pepper accuracies."
    )

    mnist_scoring_eligible: bool | None = None
    if isinstance(mnist, dict) and "error" not in mnist:
        if "scoring_eligible" in mnist:
            mnist_scoring_eligible = bool(mnist["scoring_eligible"])
        elif isinstance(mnist.get("best_validation_accuracy"), (int, float)):
            mnist_scoring_eligible = float(mnist["best_validation_accuracy"]) >= 0.95

    return {
        "available": available,
        "hint": hint,
        "mnist_metrics": mnist,
        "noise_metrics": noise,
        "mnist_scoring_eligible": mnist_scoring_eligible,
        "stage1_stack": "TensorFlow 2.x (keras) — see training/train_mnist_cnn.py",
    }
