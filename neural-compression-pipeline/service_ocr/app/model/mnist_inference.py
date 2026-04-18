"""MNIST-trained CNN digit inference (TensorFlow Keras)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_ERROR: str | None = None

_MNIST_MAX_SIDE = 96  # images larger than this are treated as documents (skip MNIST path)


def _model_path() -> Path:
    return Path(__file__).resolve().parent / "mnist-model" / "mnist_cnn.keras"


def ensure_mnist_model():
    """Load CNN once; return None if weights not present."""
    global _MODEL, _MODEL_ERROR

    if _MODEL is not None:
        return _MODEL
    if _MODEL_ERROR is not None:
        return None

    path = _model_path()
    if not path.is_file():
        _MODEL_ERROR = f"MNIST model not found at {path}"
        logger.info("%s — run training/train_mnist_cnn.py", _MODEL_ERROR)
        return None

    try:
        import tensorflow as tf

        _MODEL = tf.keras.models.load_model(path)
        logger.info("MNIST CNN loaded from %s", path)
    except Exception as exc:  # noqa: BLE001
        _MODEL_ERROR = str(exc)
        logger.exception("MNIST CNN load failed")
        return None

    return _MODEL


def infer_mnist_digit(fn_img: str | os.PathLike) -> tuple[str | None, float]:
    """
    Classify a single MNIST-sized **grayscale** crop (digits 0–9).

    Intended for images whose longest side is at most `_MNIST_MAX_SIDE` px (e.g. raw
    MNIST tiles). Larger inputs are skipped so full-page scans use the line OCR model.
    """
    path = os.fspath(fn_img)
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None, 0.0

    h, w = img.shape[:2]
    if max(h, w) > _MNIST_MAX_SIDE:
        return None, 0.0

    model = ensure_mnist_model()
    if model is None:
        return None, 0.0

    resized = cv2.resize(img, (28, 28), interpolation=cv2.INTER_AREA)
    x = (resized.astype("float32") / 255.0)[None, ..., None]
    probs = model.predict(x, verbose=0)[0]
    cls = int(np.argmax(probs))
    prob = float(np.max(probs))
    return str(cls), prob


def mnist_health() -> dict:
    ensure_mnist_model()
    if _MODEL is not None:
        return {"mnist_loaded": True, "mnist_error": None}
    return {"mnist_loaded": False, "mnist_error": _MODEL_ERROR}
