#!/bin/sh
# Daily database backup, run by cron on the server (DEPLOY.md):
#   0 0 * * * sh /home/deploy/cubing/deploy/backup.sh 2>&1 | logger -t cubing-backup
#
# Makes a consistent compressed copy in the backend-data volume
# (instance/backups/) and deletes copies older than BACKUP_KEEP_DAYS (.env, default 7).
set -eu
cd "$(dirname "$0")/.."

docker compose -f docker-compose.prod.yml exec -T backend flask backup-db
