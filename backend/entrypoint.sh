#!/bin/sh
set -e
for i in $(seq 1 10); do
  alembic upgrade head && break
  echo "database not ready yet ($i), retrying..."; sleep 2
done
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
