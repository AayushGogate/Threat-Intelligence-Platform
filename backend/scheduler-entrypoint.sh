#!/usr/bin/env bash
set -e
echo "[entrypoint] Starting ThreatIntelX Celery beat scheduler..."
sleep 8
exec celery -A app.workers.celery_app beat --loglevel=INFO
