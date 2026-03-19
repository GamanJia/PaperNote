#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
cd frontend

HOST="${FRONTEND_HOST:-127.0.0.1}"
PORT="${FRONTEND_PORT:-5173}"

npm run dev -- --host "$HOST" --port "$PORT" --strictPort
