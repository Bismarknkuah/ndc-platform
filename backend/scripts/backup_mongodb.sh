#!/usr/bin/env bash
# Backs up the MongoDB database to a timestamped directory using
# mongodump. Reads MONGO_URI / MONGO_DB_NAME from the environment (or a
# .env file in the project root), same as the Django app itself.
#
# Usage:
#   ./scripts/backup_mongodb.sh [output_dir]
#
# Requires the MongoDB Database Tools (mongodump) - install separately,
# it is NOT a Python dependency: https://www.mongodb.com/docs/database-tools/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

: "${MONGO_URI:?MONGO_URI must be set (in the environment or .env)}"
: "${MONGO_DB_NAME:?MONGO_DB_NAME must be set (in the environment or .env)}"

OUTPUT_DIR="${1:-$PROJECT_ROOT/backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$OUTPUT_DIR/$MONGO_DB_NAME-$TIMESTAMP"

mkdir -p "$DEST"

echo "Backing up '$MONGO_DB_NAME' to $DEST ..."
mongodump --uri="$MONGO_URI" --db="$MONGO_DB_NAME" --out="$DEST"

# Compress for storage/transfer.
tar -czf "$DEST.tar.gz" -C "$OUTPUT_DIR" "$(basename "$DEST")"
rm -rf "$DEST"

echo "Backup complete: $DEST.tar.gz"
echo "Upload this to off-site storage (S3/GCS/etc.) - a local-disk-only"
echo "backup does not protect against the machine it lives on failing."
