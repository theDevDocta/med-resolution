#!/bin/sh
set -e

DB_PATH="${BDPM_DB_PATH:-/app/data/bdpm.sqlite}"

if [ ! -f "$DB_PATH" ]; then
  echo "Base BDPM absente ($DB_PATH), construction initiale..."
  uv run python -m scripts.update_bdpm
fi

exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8090}"
