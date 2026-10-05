#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${COMPETITIVE_PORT:-8002}"

export POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
export POSTGRES_PORT="${POSTGRES_PORT:-5433}"
export POSTGRES_DB="${POSTGRES_DB:-boost_competitive_intelligence}"
export POSTGRES_USER="${POSTGRES_USER:-samycreates}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"

"$ROOT_DIR/scripts/bootstrap_database.sh"
cd "$ROOT_DIR/backend"
exec "$ROOT_DIR/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
