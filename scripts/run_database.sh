#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PG_BIN="${PG_BIN:-/usr/lib/postgresql/16/bin}"
PG_DATA="$ROOT_DIR/.runtime/postgres"
PG_PORT="${POSTGRES_PORT:-5433}"
PG_USER="${POSTGRES_USER:-samycreates}"

export PATH="$PG_BIN:$PATH"
mkdir -p "$PG_DATA"

if [[ ! -f "$PG_DATA/PG_VERSION" ]]; then
  initdb -D "$PG_DATA" --username="$PG_USER" --auth=trust --encoding=UTF8
fi

exec postgres -D "$PG_DATA" -p "$PG_PORT" -h 127.0.0.1 -k "$PG_DATA"
