#!/bin/sh

MODE="${SERVICE_MODE:-api}"

if [ "$MODE" = "worker" ]; then
  exec celery -A app.worker:celery_app worker --loglevel=info
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8001
