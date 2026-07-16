#!/usr/bin/env bash
# Bring the database to a usable state, then hand off to the CMD.
#
# compose already gates startup on the MySQL healthcheck, but a healthy server
# and an accepting connection are not the same instant, so we still poll.
set -euo pipefail

# Generate a signing secret on first boot rather than shipping one.
#
# A hardcoded secret in docker-compose.yml is public the moment the repo is:
# anyone who can read it can forge an admin token against any deployment that
# kept the default. But the reviewer must still get a working stack from
# `docker compose up` with zero setup, so the secret is generated here and
# persisted to the data volume — random per deployment, and stable across
# restarts so existing tokens survive.
SECRET_FILE=/app/data/.jwt_secret
if [ -z "${JWT_SECRET_KEY:-}" ]; then
    if [ ! -f "$SECRET_FILE" ]; then
        mkdir -p "$(dirname "$SECRET_FILE")"
        python -c "import secrets; print(secrets.token_urlsafe(32))" > "$SECRET_FILE"
        chmod 600 "$SECRET_FILE"
        echo "[entrypoint] generated a new JWT secret (persisted to the data volume)"
    else
        echo "[entrypoint] reusing the JWT secret from the data volume"
    fi
    JWT_SECRET_KEY="$(cat "$SECRET_FILE")"
    export JWT_SECRET_KEY
fi

echo "[entrypoint] waiting for MySQL..."
for i in {1..30}; do
    if python -c "
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings
try:
    create_engine(settings.database_url).connect().execute(text('SELECT 1'))
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo "[entrypoint] MySQL is up"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[entrypoint] MySQL unreachable after 30 attempts; giving up" >&2
        exit 1
    fi
    sleep 2
done

# Idempotent: alembic no-ops when already at head.
echo "[entrypoint] applying migrations..."
alembic upgrade head

# Idempotent: get-or-create, safe on every restart.
echo "[entrypoint] seeding roles and demo users..."
python -m scripts.seed

# The index is a mounted volume and MySQL is the source of truth, so the two can
# disagree if the volume is wiped or a previous run died mid-write. Rebuilding
# on drift beats booting into a state where search silently returns nothing.
#
# stderr is deliberately NOT redirected: reindex logs its findings there, and
# swallowing them would hide both the drift and the repair — which is exactly
# the silent failure this check exists to catch.
echo "[entrypoint] checking index consistency..."
if ! python -m scripts.reindex --check; then
    echo "[entrypoint] index drift detected, rebuilding from MySQL..."
    python -m scripts.reindex
    echo "[entrypoint] rebuild complete"
fi

echo "[entrypoint] starting: $*"
exec "$@"
