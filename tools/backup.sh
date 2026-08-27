#!/usr/bin/env bash
set -euo pipefail

compose_file="${CSP_COMPOSE_FILE:-compose.production.yml}"
env_file="${CSP_ENV_FILE:-.env.production}"
backup_dir="${CSP_BACKUP_DIR:-backups}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"

backup_file="$backup_dir/csp-${stamp}.dump"
checksum_file="${backup_file}.sha256"

export CSP_ENV_FILE="$env_file"

docker compose -f "$compose_file" exec -T postgres \
  sh -ceu 'pg_dump --format=custom --no-owner --no-acl --dbname="$POSTGRES_DB"' \
  > "$backup_file"

if [[ ! -s "$backup_file" ]]; then
  echo "backup is empty: $backup_file" >&2
  exit 1
fi

sha256sum "$backup_file" > "$checksum_file"
chmod 600 "$backup_file" "$checksum_file"
printf 'backup=%s\nchecksum=%s\n' "$backup_file" "$checksum_file"
