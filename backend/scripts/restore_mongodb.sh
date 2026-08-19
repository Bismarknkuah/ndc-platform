#!/usr/bin/env bash
# Restores a MongoDB database from a backup produced by
# backup_mongodb.sh. Destructive by default against the target database -
# confirms before proceeding.
#
# Usage:
#   ./scripts/restore_mongodb.sh path/to/backup.tar.gz
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

ARCHIVE="${1:?Usage: restore_mongodb.sh path/to/backup.tar.gz}"
if [ ! -f "$ARCHIVE" ]; then
  echo "File not found: $ARCHIVE" >&2
  exit 1
fi

echo "This will restore into database '$MONGO_DB_NAME' at $MONGO_URI,"
echo "REPLACING any documents with matching _ids. This does not delete"
echo "documents that exist in the target but not in the backup."
read -r -p "Type the database name ('$MONGO_DB_NAME') to confirm: " CONFIRM
if [ "$CONFIRM" != "$MONGO_DB_NAME" ]; then
  echo "Confirmation did not match. Aborting."
  exit 1
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

tar -xzf "$ARCHIVE" -C "$WORK_DIR"
EXTRACTED_DIR="$(find "$WORK_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

mongorestore --uri="$MONGO_URI" --db="$MONGO_DB_NAME" "$EXTRACTED_DIR/$MONGO_DB_NAME"

echo "Restore complete."
