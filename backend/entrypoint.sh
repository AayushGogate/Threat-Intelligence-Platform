#!/usr/bin/env bash
set -e
echo "[entrypoint] Starting ThreatIntelX backend API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
