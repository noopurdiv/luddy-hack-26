"""
EMNIST-Balanced CNN inference with OpenCV character segmentation.

Pipeline for any input image (no size limit):
  1. Grayscale + Otsu binarization → white chars on black (EMNIST orientation)
  2. Contour detection to find individual character bounding boxes
  3. Group into text lines; sort left-to-right within each line
  4. Detect word gaps; insert spaces where inter-character gap > median char width
  5. Resize each crop to 28×28, classify with the CNN
  6. Concatenate predictions → final text string
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_ERROR: str | None = None
_CLASS_LABELS: list[str] | None = None

# EMNIST-Balanced 47-class fallback (used when class_labels.json absent)
_FALLBACK_LABELS: list[str] = (
    [str(i) for i in range(10)]
    + [chr(ord("A") + i) for i in range(26)]
    + list("abdefghnqrt")
)


def _model_path() -> Path:
    # Prefer the H5 format (universally compatible with tf.keras in TF 2.x).
    # Fall back to the .keras ZIP format if H5 is absent.
    base = Path(__file__).resolve().parent / "mnist-model"
    h5 = base / "mnist_cnn.h5"
    if h5.is_file():
        return h5
    return base / "mnist_cnn.keras"


def _labels_path() -> Path:
    return Path(__file__).resolve().parent / "mnist-model" / "class_labels.json"


def _load_class_labels() -> list[str]:
    global _CLASS_LABELS
    if _CLASS_LABELS is not None:
        return _CLASS_LABELS
    path = _labels_path()
    if path.is_file():
        try:
            _CLASS_LABELS = json.loads(path.read_text(encoding="utf-8"))
            logger.info("Loaded %d class labels from %s", len(_CLASS_LABELS), path)
            return _CLASS_LABELS
        except Exception as exc:
            logger.warning("Could not read class_labels.json: %s", exc)
    logger.warning("Using built-in EMNIST-Balanced label map")
    _CLASS_LABELS = list(_FALLBACK_LABELS)
    return _CLASS_LABELS


def ensure_mnist_model():
    """Load CNN once; return None if weights are not present."""
    global _MODEL, _MODEL_ERROR

    if _MODEL is not None:
        return _MODEL
    if _MODEL_ERROR is not None:
        return None

    path = _model_path()
    if not path.is_file():
        _MODEL_ERROR = f"Model weights not found at {path} — run training/train_mnist_cnn.py"
        logger.info(_MODEL_ERROR)
        return None

    try:
        import tensorflow as tf

        _MODEL = tf.keras.models.load_model(str(path))
        labels = _load_class_labels()
        logger.info(
            "EMNIST CNN loaded from %s (%d classes)", path, len(labels)
        )
    except Exception as exc:  # noqa: BLE001
        _MODEL_ERROR = str(exc)
        logger.exception("CNN load failed")
        return None

    return _MODEL


# ---------------------------------------------------------------------------
# Character segmentation helpers
# ---------------------------------------------------------------------------

def _binarize(img_gray: np.ndarray) -> np.ndarray:
    """
    Return a binary image with foreground (characters) as WHITE on BLACK.

    Uses Otsu's global threshold with THRESH_BINARY_INV so that dark characters
    on a light background become white on black — matching EMNIST training orientation.
    """
    _, thresh = cv2.threshold(
        img_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    return thresh


def _segment_characters(
    thresh: np.ndarray,
) -> list[tuple[int, int, int, int]]:
    """
    Find character bounding boxes in reading order (top-to-bottom, left-to-right).

    Args:
        thresh: Binary image (white chars on black background).

    Returns:
        List of (x, y, w, h) tuples sorted in reading order.
    """
    h_img, w_img = thresh.shape[:2]
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return []

    # Filter noise: minimum contour area is 0.03% of image area, at least 2×2 px
    min_area = max(4.0, h_img * w_img * 0.0003)
    boxes = [
        cv2.boundingRect(c)
        for c in contours
        if cv2.contourArea(c) >= min_area
    ]
    boxes = [(x, y, w, h) for x, y, w, h in boxes if w >= 2 and h >= 2]

    if not boxes:
        return []

    # Group into text lines: boxes whose y-centres are within 65% of median char
    # height of each other are considered on the same line.
    median_h = float(sorted(b[3] for b in boxes)[len(boxes) // 2])
    line_thresh = median_h * 0.65

    lines: list[list[tuple[int, int, int, int]]] = []
    for box in sorted(boxes, key=lambda b: b[1]):
        cy = box[1] + box[3] / 2.0
        placed = False
        for line in lines:
            line_cy = sum(b[1] + b[3] / 2.0 for b in line) / len(line)
            if abs(cy - line_cy) <= line_thresh:
                line.append(box)
                placed = True
                break
        if not placed:
            lines.append([box])

    # Sort each line left-to-right and concatenate
    return [box for line in lines for box in sorted(line, key=lambda b: b[0])]


def _predict_crop(model, crop: np.ndarray, labels: list[str]) -> tuple[str, float]:
    """
    Pad *crop* to a square, resize to 28×28, and run CNN inference.

    Returns (predicted_character, confidence).
    """
    h, w = crop.shape[:2]
    size = max(h, w)

    # Centre the character on a black canvas (EMNIST background)
    canvas = np.zeros((size, size), dtype=np.uint8)
    oy, ox = (size - h) // 2, (size - w) // 2
    canvas[oy : oy + h, ox : ox + w] = crop

    resized = cv2.resize(canvas, (28, 28), interpolation=cv2.INTER_AREA)
    # Ensure white-digit / black-background convention (EMNIST training format).
    # If the crop is mostly white the polarity is inverted — flip it back.
    if resized.mean() > 127:
        resized = 255 - resized
    x_in = (resized.astype("float32") / 255.0)[None, ..., None]  # (1,28,28,1)

    probs = model.predict(x_in, verbose=0)[0]
    cls = int(np.argmax(probs))
    conf = float(np.max(probs))
    char = labels[cls] if cls < len(labels) else "?"
    return char, conf


# ---------------------------------------------------------------------------
# Public API (kept as infer_mnist_digit for interface compatibility)
# ---------------------------------------------------------------------------

def infer_mnist_digit(fn_img: str | os.PathLike) -> tuple[str | None, float]:
    """
    Segment *fn_img* into individual characters and classify each with the CNN.

    Despite the historic name ('mnist_digit'), this now uses an EMNIST-Balanced CNN
    and handles full alphanumeric images of any size by segmenting them into
    character crops before classification.

    Returns:
        (text, avg_confidence) — text is the concatenated character predictions;
        (None, 0.0)            — when the model is unavailable or image unreadable.
    """
    path = os.fspath(fn_img)
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        logger.warning("Could not read image at %r", path)
        return None, 0.0

    model = ensure_mnist_model()
    if model is None:
        return None, 0.0

    labels = _load_class_labels()
    thresh = _binarize(img)
    boxes = _segment_characters(thresh)

    if not boxes:
        # Nothing segmented — treat whole image as a single character
        char, conf = _predict_crop(model, thresh, labels)
        logger.info("No segments found; whole-image prediction: %r (conf=%.3f)", char, conf)
        return char, conf

    logger.info("Segmented %d character region(s)", len(boxes))

    chars: list[str] = []
    confs: list[float] = []

    # Space detection: insert a space when the gap between consecutive chars
    # exceeds 90% of the median character width.
    widths = [b[2] for b in boxes]
    median_w = float(sorted(widths)[len(widths) // 2])

    prev_x_end = 0
    for i, (x, y, w, h) in enumerate(boxes):
        if i > 0:
            gap = x - prev_x_end
            if gap > median_w * 0.9:
                chars.append(" ")
        prev_x_end = x + w

        crop = thresh[y : y + h, x : x + w]
        char, conf = _predict_crop(model, crop, labels)
        chars.append(char)
        confs.append(conf)
        logger.debug("  char[%d] %r conf=%.3f", i, char, conf)

    text = "".join(chars)
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    logger.info("Final text: %r  avg_conf=%.3f", text, avg_conf)
    return text, avg_conf


def mnist_health() -> dict:
    ensure_mnist_model()
    labels = _load_class_labels()
    if _MODEL is not None:
        return {
            "mnist_loaded": True,
            "mnist_error": None,
            "dataset": "EMNIST-Balanced",
            "num_classes": len(labels),
        }
    return {
        "mnist_loaded": False,
        "mnist_error": _MODEL_ERROR,
        "dataset": "EMNIST-Balanced",
        "num_classes": len(labels),
    }
