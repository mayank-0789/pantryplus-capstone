#!/bin/sh
set -eu
attempt=1
until alembic upgrade head; do
  if [ "$attempt" -ge 10 ]; then
    echo 'Migrations failed; refusing to start the API.' >&2
    exit 1
  fi
  echo "Migration attempt $attempt failed; retrying..." >&2
  attempt=$((attempt + 1))
  sleep 2
done
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
