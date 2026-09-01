#!/usr/bin/env bash
set -e
echo "[entrypoint] Starting ThreatIntelX Celery worker..."
# Give the API container a head start to run migrations/seed first.
sleep 5
exec celery -A app.workers.celery_app worker --loglevel=INFO --concurrency=2
