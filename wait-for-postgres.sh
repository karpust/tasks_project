#!/bin/sh
set -e

: "${DB_HOST:?DB_HOST is required}"
: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"

MAX_TRIES=20
count=0

until PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -d "$DB_NAME" -U "$DB_USER" -c '\q' > /dev/null 2>&1; do
  count=$((count + 1))
  >&2 echo "Postgres is unavailable - sleeping ($count/$MAX_TRIES)"
  if [ "$count" -ge "$MAX_TRIES" ]; then
    >&2 echo "Timeout waiting for Postgres"
    exit 1
  fi
  sleep 1
done

>&2 echo "Postgres is up - executing command"
exec "$@"

