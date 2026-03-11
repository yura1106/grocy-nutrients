#!/bin/bash

# Backup PostgreSQL database before updating Docker images.
# Run this manually before clicking "Update" in Dockge.
#
# Backups are stored in two places:
#   1. Inside the postgres volume: /var/lib/postgresql/data/backups/
#   2. On the host server:        /mnt/pool0/full-backups/other-backups/grocy_stat/

set -e

CONTAINER_NAME="grocy-reports-db-1"
DB_NAME="grocy_stat"
DB_USER="postgres"
BACKUP_DIR="/var/lib/postgresql/data/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

HOST_BACKUP_DIR="/mnt/pool0/full-backups/other-backups/grocy_stat"
HOST_BACKUP_FILE="${HOST_BACKUP_DIR}/grocy_stat_backup_${TIMESTAMP}.sql.gz"

echo "Creating backup directory inside container..."
docker exec "$CONTAINER_NAME" mkdir -p "$BACKUP_DIR"

echo "Dumping database '$DB_NAME'..."
docker exec "$CONTAINER_NAME" \
  sh -c "pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE"

echo "Backup saved to: $BACKUP_FILE (inside postgres volume)"

# Copy backup from container to host
echo "Copying backup to host: $HOST_BACKUP_FILE..."
mkdir -p "$HOST_BACKUP_DIR"
docker cp "${CONTAINER_NAME}:${BACKUP_FILE}" "$HOST_BACKUP_FILE"

echo "Backup copied to host: $HOST_BACKUP_FILE"

# Keep only the last 5 backups inside the container
echo "Cleaning up old backups in container (keeping last 5)..."
docker exec "$CONTAINER_NAME" \
  sh -c "ls -t ${BACKUP_DIR}/backup_*.sql.gz | tail -n +6 | xargs -r rm --"

# Keep only the last 5 backups on the host
echo "Cleaning up old backups on host (keeping last 5)..."
ls -t "${HOST_BACKUP_DIR}"/grocy_stat_backup_*.sql.gz | tail -n +6 | xargs -r rm --

echo "Done."
