#!/bin/sh
set -e

echo "Waiting for database..."
while ! nc -z db 5432; do sleep 1; done
echo "Database is ready!"
sleep 2

echo "Running database migrations..."
if ! alembic upgrade head; then
    echo "ERROR: Database migration failed!" >&2
    exit 1
fi
echo "Migrations completed successfully."

if [ "$ENVIRONMENT" = "development" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level warning
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level warning
fi
