#!/bin/sh
set -e

: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"
: "${DB_HOST:?DB_HOST is required}"

export PGPASSWORD="$DB_PASSWORD"

echo "Waiting for PostgreSQL..."

for _ in $(seq 1 30); do
  if psql -h "$DB_HOST" -d "$DB_NAME" -U "$DB_USER" -c '\q' > /dev/null 2>&1; then
    echo "PostgreSQL is ready"
    exec "$@"
  fi
  sleep 1
done

echo "Timeout waiting for Postgres"
exit 1
