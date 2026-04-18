# Neural Compression Pipeline

Hackathon monorepo skeleton: OCR (`service_ocr`), compression (`service_compress`), Redis, and a placeholder frontend.

## Layout

- `service_ocr/` — FastAPI on port **8001**, Celery worker module placeholder, `app/model/` for SimpleHTR (step 2).
- `service_compress/` — FastAPI on port **8002**, `app/codec/` for BWT + Huffman (step 3).
- `frontend/` — Placeholder static page under `frontend/public/` (swap in React later).

## Run with Docker Compose

```bash
docker compose up --build
```

- OCR API: http://localhost:8001  
- Compress API: http://localhost:8002  
- Redis: localhost:6379  
- Frontend placeholder: http://localhost:3000  

Health checks: `GET /health` on each API service.

## Network

All services attach to **`pipeline_net`**.
