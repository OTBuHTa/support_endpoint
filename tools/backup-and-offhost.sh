#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

backup_output="$(bash tools/backup.sh)"
printf '%s\n' "$backup_output"
backup_file="$(printf '%s\n' "$backup_output" | sed -n 's/^backup=//p' | tail -1)"

if [[ -z "$backup_file" || ! -f "$backup_file" ]]; then
  printf 'backup-and-offhost: could not identify backup dump\n' >&2
  exit 1
fi

bash tools/restore-verify.sh "$backup_file"
bash tools/backup-offhost.sh "$backup_file"

printf 'backup-and-offhost: PASS backup=%s\n' "$backup_file"
