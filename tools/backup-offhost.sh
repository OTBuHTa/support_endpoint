#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

backup_file="${1:-}"
remote="${CSP_BACKUP_SSH_REMOTE:-}"
remote_dir="${CSP_BACKUP_REMOTE_DIR:-}"

fail() {
  printf 'backup-offhost: %s\n' "$*" >&2
  exit 1
}

[[ -n "$backup_file" ]] || fail 'usage: backup-offhost.sh backups/<file>.dump'
[[ -f "$backup_file" ]] || fail "$backup_file does not exist"
[[ -f "$backup_file.sha256" ]] || fail "$backup_file.sha256 does not exist"
[[ -n "$remote" ]] || fail 'CSP_BACKUP_SSH_REMOTE is required (user@host)'
[[ -n "$remote_dir" ]] || fail 'CSP_BACKUP_REMOTE_DIR is required'

command -v ssh >/dev/null 2>&1 || fail 'ssh is not installed'
command -v scp >/dev/null 2>&1 || fail 'scp is not installed'
command -v sha256sum >/dev/null 2>&1 || fail 'sha256sum is not installed'

sha256sum -c "$backup_file.sha256"

case "$remote_dir" in
  /*) ;;
  *) fail 'CSP_BACKUP_REMOTE_DIR must be an absolute path' ;;
esac

remote_name="$(basename "$backup_file")"
checksum_name="$(basename "$backup_file.sha256")"

ssh -o BatchMode=yes -- "$remote" "mkdir -p -- '$remote_dir' && chmod 700 -- '$remote_dir'"
scp -p -- "$backup_file" "$backup_file.sha256" "$remote:$remote_dir/"

ssh -o BatchMode=yes -- "$remote" \
  "cd -- '$remote_dir' && chmod 600 -- '$remote_name' '$checksum_name' && sha256sum -c -- '$checksum_name'"

printf 'backup-offhost: PASS backup=%s destination=%s:%s/%s\n' \
  "$backup_file" "$remote" "$remote_dir" "$remote_name"
