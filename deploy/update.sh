#!/bin/sh
# Server side of deploy.ps1: loads the images it sent and restarts the service.
#   sh deploy/update.sh /tmp/cubing-images.tar
# The code (compose file, these scripts) is already updated by git pull.
set -eu
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml"
IMAGES="$1"

# The current images stay as :previous for a rollback (DEPLOY.md).
for image in cubing-backend cubing-web; do
    if docker image inspect "$image:latest" >/dev/null 2>&1; then
        docker tag "$image:latest" "$image:previous"
    fi
done

docker load -i "$IMAGES"
rm -f "$IMAGES"

# A backup before migrations run, if the backend is already up.
if $COMPOSE ps --status running --services | grep -qx backend; then
    $COMPOSE exec -T backend flask backup-db
fi

# First start: nginx needs the certificate before it can run.
set -a
. ./.env
set +a
if ! $COMPOSE run --rm --no-deps --entrypoint test certbot -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem"; then
    echo "No certificate yet, getting one."
    sh deploy/cert.sh
fi

$COMPOSE up -d --remove-orphans
docker image prune -f
$COMPOSE ps
