from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.codec import pipeline

router = APIRouter()


class CompressBody(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=100_000,
        description="Plain text to compress (non-empty, at most 100000 characters)",
    )

    model_config = {"json_schema_extra": {"example": {"text": "hello world"}}}


class DecompressBody(BaseModel):
    compressed_b64: str = Field(..., description="Base64 blob from /compress")
    bwt_index: int = Field(..., description="BWT primary index from /compress")

    model_config = {
        "json_schema_extra": {
            "example": {"compressed_b64": "...", "bwt_index": 0},
        },
    }


@router.post("/compress")
def compress_payload(body: CompressBody) -> dict[str, Any]:
    try:
        return pipeline.compress(body.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/decompress")
def decompress_payload(body: DecompressBody) -> dict[str, Any]:
    try:
        text = pipeline.decompress(body.compressed_b64, body.bwt_index)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"text": text, "decompressed_size": len(text.encode("utf-8"))}
