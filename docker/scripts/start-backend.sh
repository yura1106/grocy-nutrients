#!/bin/sh

echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is ready!"

# Wait a bit to ensure Postgres is fully ready
sleep 2

# Initialize database and run migrations
python -c "from app.db.init_db import init_db; init_db()"
alembic upgrade head

# Start the application based on environment
if [ "$ENVIRONMENT" = "development" ]; then
    # Development mode with hot reload
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    # Production mode with multiple workers
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
fi 