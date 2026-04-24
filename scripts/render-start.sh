#!/bin/sh
set -e
export PORT="${PORT:-10000}"
# Migraciones antes de levantar (Render inyecta DATABASE_URL).
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
