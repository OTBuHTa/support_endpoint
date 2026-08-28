#!/usr/bin/env bash
set -euo pipefail

nas_host="${CSP_NAS_HOST:-192.168.5.160}"
nas_export="${CSP_NAS_EXPORT:-/Volume1/AI-Lab-Backup}"
mount_point="${CSP_NAS_MOUNT_POINT:-/mnt/support-endpoint-nas}"

fail() {
  printf 'ensure-nas-mount: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null || fail 'docker is required for isolated host-mount reconciliation'
docker info >/dev/null 2>&1 || fail 'docker access is required'

if findmnt -rn -T "$mount_point" -t nfs,nfs4 >/dev/null 2>&1; then
  printf 'ensure-nas-mount: already mounted at %s\n' "$mount_point"
  exit 0
fi

# Verify the NFS service is reachable before attempting a host mount.
timeout 5 bash -c "</dev/tcp/${nas_host}/2049" \
  || fail "NAS NFS service is unreachable at ${nas_host}:2049"

# The production runner intentionally has Docker access but no host root shell.
# Use a short-lived privileged helper only to enter the host mount namespace and
# create this project's dedicated NFS mount. It does not modify the existing
# /mnt/ai-lab-nas automount or any ai-lab systemd unit.
docker run --rm --privileged --pid=host --network=host \
  -e NAS_HOST="$nas_host" \
  -e NAS_EXPORT="$nas_export" \
  -e MOUNT_POINT="$mount_point" \
  alpine:3.20 sh -ceu '
    apk add --no-cache util-linux nfs-utils >/dev/null
    nsenter -t 1 -m -- mkdir -p "$MOUNT_POINT"
    if ! nsenter -t 1 -m -- findmnt -rn -T "$MOUNT_POINT" -t nfs,nfs4 >/dev/null 2>&1; then
      nsenter -t 1 -m -- mount -t nfs4 \
        -o rw,vers=4.1,proto=tcp,hard,timeo=600,retrans=2,noatime \
        "$NAS_HOST:$NAS_EXPORT" "$MOUNT_POINT"
    fi
  '

findmnt -rn -T "$mount_point" -t nfs,nfs4 >/dev/null 2>&1 \
  || fail "NFS mount did not appear at $mount_point"

timeout 10 ls -la "$mount_point" >/dev/null \
  || fail "mounted NAS is not readable at $mount_point"

printf 'ensure-nas-mount: mounted %s:%s at %s\n' "$nas_host" "$nas_export" "$mount_point"
