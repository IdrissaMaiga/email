#!/bin/bash
# Backup PostgreSQL database from Docker volume to a file
# Usage: ./backup_db.sh <backup_file.sql>

set -e

BACKUP_FILE=${1:-backup_$(date +%Y%m%d_%H%M%S).sql}
CONTAINER=$(docker ps -qf "name=email_db_1")

if [ -z "$CONTAINER" ]; then
  echo "Database container not running!"
  exit 1
fi

echo "Dumping database to $BACKUP_FILE ..."
docker exec -t $CONTAINER pg_dump -U postgres email_sender_db > "$BACKUP_FILE"
echo "Backup complete: $BACKUP_FILE"
