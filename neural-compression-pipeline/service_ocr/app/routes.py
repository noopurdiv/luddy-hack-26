import base64
import logging
import os
import uuid
from typing import Union

import httpx
from celery.result import AsyncResult
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.model.inference import model_health_status, run_inference
from app.ocr_metrics import evaluate_scoring_eligibility, load_ocr_accuracy_payload
from app.worker import celery_app, process_ocr_and_compress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["ocr"])

_ALLOWED_IMAGE_TYPES = frozenset({"image/png", "image/jpeg"})


@router.get("/accuracy")
def get_ocr_accuracy_metrics() -> dict:
    """Validation / test accuracies persisted after training (MNIST CNN + optional noise eval)."""
    return load_ocr_accuracy_payload()


def _reject_media_type(raw_type: str) -> JSONResponse | None:
    content_type = raw_type.split(";")[0].strip().lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        logger.info("Rejected upload: unsupported content type %r", raw_type)
        return JSONResponse(
            status_code=422,
            content={
                "error": "unsupported_media_type",
                "detail": f"Expected image/png or image/jpeg, got {raw_type!r}",
            },
        )
    return None


_COMPRESS_URL = os.environ.get(
    "COMPRESS_SERVICE_URL",
    "http://service_compress:8002/compress",
)


def _call_compress(text: str) -> dict | None:
    """POST recognized text to the compression service; return result or None on failure."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(_COMPRESS_URL, json={"text": text})
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Compression service call failed: %s", exc)
        return None


@router.post("", response_model=None)
async def ocr_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="PNG or JPEG image of handwritten text"),
    reference_text: str | None = Form(
        None,
        description="Optional ground-truth text to compute character_accuracy_vs_reference",
    ),
    scoring_mode: bool = Form(
        False,
        description=(
            "Set true to enforce the ≥95% validation-accuracy gate and CNN-only backend "
            "requirement. Returns HTTP 412 when either condition is not met."
        ),
    ),
) -> Union[dict, JSONResponse]:
    raw_type = image.content_type or ""
    bad = _reject_media_type(raw_type)
    if bad is not None:
        return bad

    filename = image.filename or "upload"
    payload = await image.read()
    if not payload:
        return JSONResponse(
            status_code=422,
            content={
                "error": "empty_file",
                "detail": "Uploaded image is empty",
            },
        )

    # ── pre-inference scoring gate ────────────────────────────────────────────
    eligibility = evaluate_scoring_eligibility()
    if scoring_mode and not eligibility["eligible"]:
        return JSONResponse(
            status_code=412,
            content={
                "error": "scoring_gate_failed",
                "reason": eligibility["reason_code"],
                "detail": (
                    "Model has not met the ≥95% validation-accuracy requirement. "
                    "Train with training/train_mnist_cnn.py first."
                ),
                "scoring_eligibility": eligibility,
            },
        )

    logger.info("OCR request file=%r bytes=%d scoring_mode=%s", filename, len(payload), scoring_mode)

    ref = reference_text.strip() if reference_text else None
    result = run_inference(
        payload,
        background_tasks=background_tasks,
        reference_text=ref,
    )

    # ── post-inference scoring gate (CNN backend required) ────────────────────
    if scoring_mode and result.get("ocr_backend") != "mnist_cnn":
        return JSONResponse(
            status_code=412,
            content={
                "error": "scoring_gate_failed",
                "reason": "non_cnn_backend",
                "detail": (
                    f"OCR output came from '{result.get('ocr_backend')}', not the custom "
                    "MNIST CNN. Only CNN-produced output is eligible for scoring."
                ),
                "ocr_backend": result.get("ocr_backend"),
                "scoring_eligibility": eligibility,
            },
        )

    # ── inline OCR → compression chaining ────────────────────────────────────
    ocr_text = result.get("text") or ""
    compression: dict | None = None
    if ocr_text.strip():
        compression = _call_compress(ocr_text)

    response: dict = {
        "text": ocr_text,
        "confidence": result["confidence"],
        "filename": filename,
        "ocr_backend": result.get("ocr_backend"),
        "mnist_validation_accuracy_recorded": result.get("mnist_validation_accuracy_recorded"),
        "character_accuracy_vs_reference": result.get("character_accuracy_vs_reference"),
        "scoring_eligible": eligibility["eligible"],
        "scoring_eligibility": eligibility,
        "compression": compression,
    }
    if "error" in result:
        response["error"] = result["error"]
    return response


@router.post("/async", response_model=None)
async def ocr_async(image: UploadFile = File(..., description="PNG or JPEG image")) -> Union[dict, JSONResponse]:
    raw_type = image.content_type or ""
    bad = _reject_media_type(raw_type)
    if bad is not None:
        return bad

    payload = await image.read()
    if not payload:
        return JSONResponse(
            status_code=422,
            content={
                "error": "empty_file",
                "detail": "Uploaded image is empty",
            },
        )

    image_b64 = base64.b64encode(payload).decode("ascii")
    job_id = str(uuid.uuid4())
    process_ocr_and_compress.apply_async(args=[image_b64, job_id], task_id=job_id)
    logger.info("Queued OCR+compress job_id=%s", job_id)
    return {"job_id": job_id, "status": "queued"}


@router.get("/job/{job_id}")
def ocr_job_status(job_id: str) -> dict:
    res = AsyncResult(job_id, app=celery_app)
    if res.state == "SUCCESS":
        return {"job_id": job_id, "status": "done", "result": res.result}
    if res.state == "FAILURE":
        err_msg = str(res.result) if res.result is not None else "task failed"
        return {"job_id": job_id, "status": "error", "error": err_msg}
    return {"job_id": job_id, "status": "pending"}


@router.get("/health", response_model=None)
def ocr_health() -> Union[dict, JSONResponse]:
    """Healthy if at least one CNN (MNIST digit model or SimpleHTR line model) loads."""
    info = model_health_status()
    ok = info.get("simple_htr_loaded") or info.get("mnist_loaded")
    if ok:
        return {"status": "ok", **info}
    return JSONResponse(
        status_code=503,
        content={"status": "error", **info},
    )
