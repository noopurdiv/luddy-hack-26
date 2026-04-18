"""Celery worker for OCR + downstream compression."""

from __future__ import annotations

import base64
import logging
import os

import httpx
from celery import Celery

logger = logging.getLogger(__name__)

CELERY_BROKER = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "ocr_worker",
    broker=CELERY_BROKER,
    backend=CELERY_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)


@celery_app.task(name="ocr_worker.process_ocr_and_compress", bind=False)
def process_ocr_and_compress(image_b64: str, job_id: str) -> dict:
    """
    Decode image, run OCR inference, POST recognized text to the compress service.
    """
    image_bytes = base64.b64decode(image_b64)

    from app.model.inference import run_inference

    ocr_result = run_inference(image_bytes, background_tasks=None)

    raw_text = ocr_result.get("text") or ""

    compress_url = os.environ.get(
        "COMPRESS_SERVICE_URL",
        "http://service_compress:8002/compress",
    )
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            compress_url,
            json={"text": raw_text},
        )
        resp.raise_for_status()
        compress_result = resp.json()

    return {
        "job_id": job_id,
        "ocr": ocr_result,
        "compression": compress_result,
    }
