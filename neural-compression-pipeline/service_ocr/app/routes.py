import base64
import logging
import uuid
from typing import Union

from celery.result import AsyncResult
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.model.inference import model_health_status, run_inference
from app.ocr_metrics import load_ocr_accuracy_payload
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


@router.post("", response_model=None)
async def ocr_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="PNG or JPEG image of handwritten text"),
    reference_text: str | None = Form(
        None,
        description="Optional ground-truth text to compute character_accuracy_vs_reference",
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

    logger.info("OCR request file=%r bytes=%d", filename, len(payload))

    ref = reference_text.strip() if reference_text else None
    result = run_inference(
        payload,
        background_tasks=background_tasks,
        reference_text=ref,
    )

    response: dict = {
        "text": result.get("text") or "",
        "confidence": result["confidence"],
        "filename": filename,
        "ocr_backend": result.get("ocr_backend"),
        "mnist_validation_accuracy_recorded": result.get("mnist_validation_accuracy_recorded"),
        "character_accuracy_vs_reference": result.get("character_accuracy_vs_reference"),
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
