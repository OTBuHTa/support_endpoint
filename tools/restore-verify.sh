#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <backup.dump>" >&2
  exit 2
fi

backup_file="$1"
checksum_file="${backup_file}.sha256"
compose_file="${CSP_COMPOSE_FILE:-compose.production.yml}"
env_file="${CSP_ENV_FILE:-.env.production}"
verify_db="csp_restore_verify_$(date -u +%Y%m%d%H%M%S)_$$"

if [[ ! -s "$backup_file" ]]; then
  echo "backup does not exist or is empty: $backup_file" >&2
  exit 1
fi

if [[ -f "$checksum_file" ]]; then
  sha256sum --check "$checksum_file"
else
  echo "warning: checksum file not found: $checksum_file" >&2
fi

export CSP_ENV_FILE="$env_file"

compose() {
  docker compose --env-file "$env_file" -f "$compose_file" "$@"
}

cleanup() {
  compose exec -T postgres \
    sh -ceu 'dropdb --username="$POSTGRES_USER" --if-exists --force "$1"' sh "$verify_db" \
    >/dev/null 2>&1 || true
}
trap cleanup EXIT

compose exec -T postgres \
  sh -ceu 'createdb --username="$POSTGRES_USER" "$1"' sh "$verify_db"

compose exec -T postgres \
  sh -ceu 'pg_restore --username="$POSTGRES_USER" --exit-on-error --no-owner --no-acl --dbname="$1"' \
  sh "$verify_db" < "$backup_file"

compose exec -T postgres \
  sh -ceu 'psql --username="$POSTGRES_USER" --dbname="$1" --tuples-only --no-align --command="SELECT count(*) FROM alembic_version;"' \
  sh "$verify_db" \
  | grep -Eq '^[1-9][0-9]*$'

echo "restore verification succeeded: $verify_db"
