# Support Endpoint production edge and off-host backup

This runbook closes the two environment-specific release gates that repository CI cannot simulate: a dedicated public HTTPS origin and an off-host verified PostgreSQL backup destination.

## Isolation rules

- Do not reuse another project's Cloudflare Tunnel, token, credentials, hostname, systemd unit or backup destination.
- Keep the application listener on `127.0.0.1:8180`.
- Keep `/opt/support-endpoint/.env.production` mode `600`.
- Keep tunnel credentials and backup destination configuration under `/etc/support-endpoint/`, never in Git.
- A stable release is not complete until `tools/production-edge-check.sh` passes against the real HTTPS origin and `tools/backup-and-offhost.sh` completes against the real remote backup destination.

## Dedicated Cloudflare Tunnel

Create a new Cloudflare Tunnel dedicated to Support Endpoint and choose a dedicated hostname. Do not attach an existing tunnel used by another application.

Prepare the host directory:

```bash
sudo install -d -m 700 -o cloudflared -g cloudflared /etc/support-endpoint
```

Copy `deploy/cloudflared-support-endpoint.yml.example` to `/etc/support-endpoint/cloudflared.yml`, replace the tunnel UUID and hostname, and install the credentials JSON generated for that tunnel as `/etc/support-endpoint/cloudflared-credentials.json`.

The only application ingress must be:

```yaml
service: http://127.0.0.1:8180
```

Install the dedicated unit:

```bash
sudo install -m 644 deploy/systemd/cloudflared-support-endpoint.service \
  /etc/systemd/system/cloudflared-support-endpoint.service
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared-support-endpoint.service
```

Do not stop, replace or edit the host's generic `cloudflared.service` as part of this deployment.

Update `/opt/support-endpoint/.env.production` so `CORS_ALLOW_ORIGINS` is the exact new HTTPS origin. Keep `CSP_WEB_BIND=127.0.0.1:8180`, then redeploy through the guarded production workflow.

Validate from the host and through the public edge:

```bash
export CSP_ENV_FILE=.env.production
export CSP_PUBLIC_ORIGIN=https://REPLACE_WITH_SUPPORT_HOSTNAME
export CSP_EXPECT_BUILD_REVISION="$(git rev-parse HEAD)"
RELEASE_VERSION=0.9.0-rc1 bash tools/production-edge-check.sh
```

The check fails closed if the placeholder origin remains, the web bind is not loopback-only, health/readiness are degraded, version/build identity drift, the public origin is not HTTPS, or API documentation is exposed.

## Off-host PostgreSQL backups over SSH

Use a dedicated remote account with key-only authentication and a destination not mounted from the application host. Pre-provision the remote directory and pin the destination host key for the `support-runner` account before enabling the timer.

Install the host configuration:

```bash
sudo install -d -m 700 /etc/support-endpoint
sudo install -m 600 deploy/support-endpoint-backup.env.example \
  /etc/support-endpoint/backup-offhost.env
sudoedit /etc/support-endpoint/backup-offhost.env
```

Set:

- `CSP_BACKUP_SSH_REMOTE=user@host`
- `CSP_BACKUP_REMOTE_DIR=/absolute/remote/path`

Run one manual full rehearsal before scheduling:

```bash
cd /opt/support-endpoint
bash tools/backup-and-offhost.sh
```

This sequence creates a fresh custom-format PostgreSQL dump, verifies its local checksum, restores it into an isolated verification database, transfers both dump and checksum to the remote host, then verifies SHA-256 again on the remote host.

Install the timer only after the manual rehearsal succeeds:

```bash
sudo install -m 644 deploy/systemd/support-endpoint-backup.service \
  /etc/systemd/system/support-endpoint-backup.service
sudo install -m 644 deploy/systemd/support-endpoint-backup.timer \
  /etc/systemd/system/support-endpoint-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now support-endpoint-backup.timer
systemctl list-timers support-endpoint-backup.timer
```

The timer runs daily with a randomized delay. Local backups remain under `/opt/support-endpoint/backups/`; retention and encrypted storage policy on the remote destination must be managed independently.

## Stable-release gate

Before promoting `v0.9.0-rc1` to stable, record evidence for all of the following:

1. Dedicated HTTPS hostname resolves and serves Support Endpoint only.
2. `tools/production-edge-check.sh` passes against that public origin.
3. `CORS_ALLOW_ORIGINS` equals the real HTTPS origin and contains no placeholder.
4. The dedicated `cloudflared-support-endpoint.service` is active without a restart loop.
5. A fresh production backup passes local checksum and isolated restore verification.
6. The same backup is present off-host and passes remote SHA-256 verification.
7. The daily backup timer is enabled and its first scheduled run succeeds.
