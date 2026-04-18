"""
OCR inference: MNIST-trained CNN (digits) → SimpleHTR line model → Tesseract fallback.

MNIST CNN weights: ``app/model/mnist-model/mnist_cnn.keras`` (see ``training/train_mnist_cnn.py``).
SimpleHTR weights: ``app/model/line-model/``.
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections import namedtuple
from pathlib import Path

import cv2
import numpy as np
from fastapi import BackgroundTasks

from app.char_accuracy import character_accuracy_ratio
from app.model.dataloader_iam import Batch
from app.model.mnist_inference import ensure_mnist_model, infer_mnist_digit
from app.model.model import DecoderType, Model
from app.model.preprocessor import Preprocessor
from app.ocr_metrics import recorded_mnist_validation_accuracy

logger = logging.getLogger(__name__)

DecoderOutput = namedtuple("DecoderOutput", ["text", "probability"])

_LINE_MODE = True

_MODEL: Model | None = None
_MODEL_ERROR: str | None = None


def _img_height() -> int:
    return 32


def _img_size(*, line_mode: bool) -> tuple[int, int]:
    if line_mode:
        return 256, _img_height()
    return 128, _img_height()


def infer(model: Model, fn_img: str | os.PathLike) -> DecoderOutput:
    """
    Run SimpleHTR recognition on a single image file (grayscale PNG/JPEG path).

    Mirrors ``infer`` from SimpleHTR's ``main.py`` using the **line** image geometry
    (256x32) to match pretrained line-model checkpoints.
    """
    path = os.fspath(fn_img)
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image at {path!r}")

    preprocessor = Preprocessor(
        _img_size(line_mode=_LINE_MODE),
        dynamic_width=True,
        padding=16,
    )
    processed = preprocessor.process_img(img)
    batch = Batch([processed], None, 1)
    recognized, probability = model.infer_batch(batch, calc_probability=True)
    prob_arr = None if probability is None else np.asarray(probability).reshape(-1)
    prob = float(prob_arr[0]) if prob_arr is not None and prob_arr.size else 0.0
    return DecoderOutput(text=recognized[0], probability=prob)


def _ensure_simple_htr_model() -> Model | None:
    """Load TF line model once; record failure reason for health checks."""
    global _MODEL, _MODEL_ERROR

    if _MODEL is not None:
        return _MODEL
    if _MODEL_ERROR is not None:
        return None

    model_dir = Path(__file__).resolve().parent / "line-model"
    char_list_file = model_dir / "charList.txt"
    try:
        with open(char_list_file, encoding="utf-8") as f:
            char_list = list(f.read())
        loaded = Model(
            char_list,
            DecoderType.BestPath,
            must_restore=True,
            dump=False,
            model_dir=str(model_dir),
        )
    except Exception as exc:  # noqa: BLE001 — surface any init/IO/TF failure
        _MODEL_ERROR = str(exc)
        logger.exception("SimpleHTR model initialization failed")
        return None

    _MODEL = loaded
    logger.info("SimpleHTR line-model ready (dir=%s)", model_dir)
    return loaded


def _unlink_temp(path: str) -> None:
    try:
        os.unlink(path)
    except OSError as exc:
        logger.warning("Failed to remove temp file %s: %s", path, exc)


def _tesseract_ocr(img_path: str) -> tuple[str, float]:
    """Run Tesseract on a full document or multi-line image."""
    try:
        import pytesseract
        from PIL import Image as PILImage

        img = PILImage.open(img_path)
        text = pytesseract.image_to_string(img, config="--psm 6")
        return text.strip(), 0.85
    except Exception as exc:
        logger.warning("Tesseract OCR failed: %s", exc)
        return "", 0.0


# Lowered from 0.82 (MNIST 10-class) to 0.40 because:
#  - EMNIST-Balanced is a 47-class problem — per-class max softmax scores are
#    naturally lower even for correct predictions.
#  - Segmentation averages confidence over multiple characters, smoothing noise.
_MNIST_CONF_THRESHOLD = 0.40


def run_inference(
    image_bytes: bytes,
    *,
    background_tasks: BackgroundTasks | None = None,
    reference_text: str | None = None,
) -> dict:
    """
    Run OCR on image bytes.

    Order:
      1. EMNIST-Balanced CNN with OpenCV character segmentation (primary path,
         any image size, 47 alphanumeric classes).
      2. SimpleHTR line CNN — fallback when CNN returns empty text.
      3. Tesseract — last-resort fallback.

    ``reference_text`` (optional): ground-truth transcript; response includes
    ``character_accuracy_vs_reference`` (normalized edit-distance accuracy).

    ``mnist_validation_accuracy_recorded`` is always read from persisted training
    metrics when present.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp_path = tmp.name
    try:
        tmp.write(image_bytes)
        tmp.flush()
    finally:
        tmp.close()

    try:
        text = ""
        confidence = 0.0
        ocr_backend: str | None = None

        mnist_recorded_val = recorded_mnist_validation_accuracy()

        mnist_digit, mnist_prob = infer_mnist_digit(tmp_path)
        if mnist_digit is not None and mnist_prob >= _MNIST_CONF_THRESHOLD:
            logger.info(
                "MNIST CNN prediction digit=%s prob=%.4f",
                mnist_digit,
                mnist_prob,
            )
            text = mnist_digit
            confidence = mnist_prob
            ocr_backend = "mnist_cnn"

        model = _ensure_simple_htr_model()

        if not text.strip() and model is not None:
            try:
                decoded = infer(model, tmp_path)
                text = decoded.text
                confidence = float(decoded.probability)
                ocr_backend = "simple_htr"
            except Exception as exc:
                logger.warning("SimpleHTR inference failed: %s", exc)

        if not text.strip():
            logger.info("MNIST/STTR empty or skipped; trying Tesseract")
            text, confidence = _tesseract_ocr(tmp_path)
            ocr_backend = "tesseract"

        ref = reference_text.strip() if reference_text else ""
        char_vs_ref: float | None = None
        if ref:
            char_vs_ref = character_accuracy_ratio(text, ref)

        return {
            "text": text,
            "confidence": confidence,
            "ocr_backend": ocr_backend,
            "mnist_validation_accuracy_recorded": mnist_recorded_val,
            "character_accuracy_vs_reference": char_vs_ref,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("OCR inference failed")
        return {
            "text": "",
            "confidence": 0.0,
            "error": str(exc),
            "ocr_backend": None,
            "mnist_validation_accuracy_recorded": recorded_mnist_validation_accuracy(),
            "character_accuracy_vs_reference": None,
        }
    finally:
        if background_tasks is not None:
            background_tasks.add_task(_unlink_temp, tmp_path)
        else:
            _unlink_temp(tmp_path)


def model_health_status() -> dict:
    """Report SimpleHTR + MNIST CNN load status."""
    from app.model.mnist_inference import mnist_health

    _ensure_simple_htr_model()
    mn = mnist_health()

    line_ok = _MODEL is not None
    return {
        "simple_htr_loaded": line_ok,
        "simple_htr_error": None if line_ok else _MODEL_ERROR,
        **mn,
    }
