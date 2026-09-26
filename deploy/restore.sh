#!/bin/sh
# Restores the database from a backup in the backend-data volume.
#   sh deploy/restore.sh                                  list backups
#   sh deploy/restore.sh cubing-20261205-000000.db.gz     restore that one
#
# The backend is stopped while restoring, so the site shows errors for a few
# seconds. The current database is saved first as …-before-restore.db.gz.
set -eu
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml"

if [ $# -ne 1 ]; then
    echo "Backups (UTC time in the name):"
    $COMPOSE run --rm --no-deps -T backend ls -l instance/backups
    echo
    echo "Restore: sh deploy/restore.sh <file name>"
    exit 1
fi

$COMPOSE stop backend
# Start the backend again even if the restore fails.
trap '$COMPOSE start backend' EXIT
$COMPOSE run --rm --no-deps -T backend flask restore-db "$1"
