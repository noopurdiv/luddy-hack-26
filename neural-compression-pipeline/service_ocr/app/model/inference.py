"""
SimpleHTR inference for the OCR service.

Loads checkpoint weights from ``app/model/line-model/`` (see README).
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

from app.model.dataloader_iam import Batch
from app.model.model import DecoderType, Model
from app.model.preprocessor import Preprocessor

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


def _ensure_model() -> Model | None:
    """Load TF model once; record failure reason for health checks."""
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
    logger.info("SimpleHTR model ready (dir=%s)", model_dir)
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


def run_inference(
    image_bytes: bytes,
    *,
    background_tasks: BackgroundTasks | None = None,
) -> dict:
    """
    Run OCR on image bytes.

    Tries SimpleHTR first (optimised for single handwritten lines).  Falls back to
    Tesseract when SimpleHTR returns empty text or when the model is unavailable,
    which handles full document scans and printed text correctly.
    """
    model = _ensure_model()

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

        if model is not None:
            try:
                decoded = infer(model, tmp_path)
                text = decoded.text
                confidence = float(decoded.probability)
            except Exception as exc:
                logger.warning("SimpleHTR inference failed, falling back to Tesseract: %s", exc)

        if not text.strip():
            logger.info("SimpleHTR returned empty text; running Tesseract fallback")
            text, confidence = _tesseract_ocr(tmp_path)

        return {"text": text, "confidence": confidence}
    except Exception as exc:  # noqa: BLE001
        logger.exception("OCR inference failed")
        return {"text": "", "confidence": 0.0, "error": str(exc)}
    finally:
        if background_tasks is not None:
            background_tasks.add_task(_unlink_temp, tmp_path)
        else:
            _unlink_temp(tmp_path)


def model_health_status() -> dict:
    """Return whether the lazy singleton loaded successfully."""
    _ensure_model()
    if _MODEL is not None:
        return {"model_loaded": True, "error": None}
    return {"model_loaded": False, "error": _MODEL_ERROR}
