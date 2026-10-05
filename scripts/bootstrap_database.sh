#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PG_BIN="${PG_BIN:-/usr/lib/postgresql/16/bin}"
PG_PORT="${POSTGRES_PORT:-5433}"
PG_HOST="${POSTGRES_HOST:-127.0.0.1}"
PG_USER="${POSTGRES_USER:-samycreates}"
PG_DB="${POSTGRES_DB:-boost_competitive_intelligence}"

export PATH="$PG_BIN:$PATH"

until pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" >/dev/null 2>&1; do
  sleep 1
done

if ! psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '$PG_DB'" | grep -q 1; then
  createdb -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" "$PG_DB"
fi

if ! psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -tAc \
  "SELECT to_regclass('public.competitors') IS NOT NULL" | grep -q t; then
  for sql_file in "$ROOT_DIR"/database/schema/*.sql; do
    psql -v ON_ERROR_STOP=1 -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -f "$sql_file"
  done
  for sql_file in "$ROOT_DIR"/database/seed/*.sql; do
    psql -v ON_ERROR_STOP=1 -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -f "$sql_file"
  done
fi
