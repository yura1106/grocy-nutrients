#!/bin/bash

# Backup PostgreSQL database before updating Docker images.
# Run this manually before clicking "Update" in Dockge.
#
# Backups are stored inside the postgres volume at:
#   /var/lib/postgresql/data/backups/
# They persist across container restarts and image updates.

set -e

CONTAINER_NAME="grocy-reports-db-1"
DB_NAME="grocy_stat"
DB_USER="postgres"
BACKUP_DIR="/var/lib/postgresql/data/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

echo "Creating backup directory inside container..."
docker exec "$CONTAINER_NAME" mkdir -p "$BACKUP_DIR"

echo "Dumping database '$DB_NAME'..."
docker exec "$CONTAINER_NAME" \
  sh -c "pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE"

echo "Backup saved to: $BACKUP_FILE (inside postgres volume)"

# Keep only the last 5 backups
echo "Cleaning up old backups (keeping last 5)..."
docker exec "$CONTAINER_NAME" \
  sh -c "ls -t ${BACKUP_DIR}/backup_*.sql.gz | tail -n +6 | xargs -r rm --"

echo "Done."
