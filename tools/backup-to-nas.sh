#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

mount_point="${CSP_NAS_MOUNT_POINT:-/mnt/support-endpoint-nas}"
nas_root="${CSP_NAS_BACKUP_DIR:-$mount_point/support-endpoint}"
retention_days="${CSP_NAS_RETENTION_DAYS:-30}"

fail() {
  printf 'backup-to-nas: %s\n' "$*" >&2
  exit 1
}

findmnt -rn -T "$mount_point" -t nfs,nfs4 >/dev/null 2>&1 \
  || fail "$mount_point is not an NFS mount; run tools/ensure-nas-mount.sh first"
mkdir -p "$nas_root" || fail "cannot create $nas_root"
[[ -w "$nas_root" ]] || fail "$nas_root is not writable"

backup_output="$(CSP_ENV_FILE="${CSP_ENV_FILE:-.env.production}" bash tools/backup.sh)"
printf '%s\n' "$backup_output"
backup_file="$(printf '%s\n' "$backup_output" | sed -n 's/^backup=//p' | tail -1)"
[[ -n "$backup_file" && -f "$backup_file" ]] || fail 'could not identify backup file'

bash tools/restore-verify.sh "$backup_file"
checksum_file="$backup_file.sha256"
[[ -f "$checksum_file" ]] || fail "missing checksum $checksum_file"

base="$(basename "$backup_file")"
checksum_base="$(basename "$checksum_file")"
partial="$nas_root/$base.partial"
partial_checksum="$nas_root/$checksum_base.partial"

cp --preserve=mode,timestamps "$backup_file" "$partial"
cp --preserve=mode,timestamps "$checksum_file" "$partial_checksum"
mv -f "$partial" "$nas_root/$base"
mv -f "$partial_checksum" "$nas_root/$checksum_base"

(
  cd "$nas_root"
  sha256sum -c "$checksum_base"
)

find "$nas_root" -maxdepth 1 -type f -name 'csp-*.dump' -mtime "+$retention_days" -delete
find "$nas_root" -maxdepth 1 -type f -name 'csp-*.dump.sha256' -mtime "+$retention_days" -delete

printf 'nas_backup=%s\n' "$nas_root/$base"
printf 'nas_retention_days=%s\n' "$retention_days"
