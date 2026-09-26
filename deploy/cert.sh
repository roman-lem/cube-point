#!/bin/sh
# Gets the Let's Encrypt certificate for DOMAIN, www.DOMAIN and EXTRA_DOMAINS (.env),
# or extends it after a domain is added to EXTRA_DOMAINS. Renewal is automatic
# (the certbot container); this script is only for the first time and for new domains.
#
# Before the site runs, certbot answers Let's Encrypt itself on port 80 (standalone).
# While it runs, nginx serves the check files (webroot) and reloads afterwards.
set -eu
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker-compose.prod.yml"

set -a
. ./.env
set +a
: "${DOMAIN:?Set DOMAIN in .env}"
: "${LETSENCRYPT_EMAIL:?Set LETSENCRYPT_EMAIL in .env}"

domains="-d $DOMAIN -d www.$DOMAIN"
for extra in ${EXTRA_DOMAINS:-}; do
    domains="$domains -d $extra"
done

options="--cert-name $DOMAIN $domains --email $LETSENCRYPT_EMAIL --agree-tos --no-eff-email --non-interactive --expand"

if $COMPOSE ps --status running --services | grep -qx web; then
    $COMPOSE run --rm --no-deps --entrypoint certbot certbot \
        certonly --webroot -w /var/www/certbot $options
    $COMPOSE exec web nginx -s reload
else
    $COMPOSE run --rm --no-deps -p 80:80 --entrypoint certbot certbot \
        certonly --standalone $options
fi
