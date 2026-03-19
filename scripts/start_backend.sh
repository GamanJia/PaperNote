#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
cd backend

HOST="${BACKEND_HOST:-127.0.0.1}"
PORT="${BACKEND_PORT:-8000}"

uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
