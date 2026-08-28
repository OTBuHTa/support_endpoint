# Production deployment — v0.9.0

This runbook describes the hardened single-host deployment path for Support Endpoint. It is intentionally separate from the development compose file.

## Security invariants

- Use `compose.production.yml`, not the development compose file, for external service.
- Keep the web listener on loopback by default (`127.0.0.1:8180`) and expose it through a dedicated host reverse proxy or tunnel.
- The API is not published on a host port in production; nginx reaches it over the private Docker backend network.
- The backend Docker network is `internal: true` and remains separate from AI-project-SRV networks and volumes.
- API, scheduler and web containers use read-only root filesystems where applicable, `no-new-privileges`, and reduced Linux capabilities.
- FastAPI docs/OpenAPI are disabled when `APP_ENV=production`.
- Production startup fails if the JWT secret is unsafe, bootstrap is enabled, auth rate limiting is disabled, HSTS mode is disabled, CORS origins are empty, the metrics bearer token is too short, or the SLA scheduler interval is unsafe.
- Browser refresh sessions use an HttpOnly, SameSite=Strict cookie with server-side rotation/revocation.
- The SLA scheduler is a separate process and uses a PostgreSQL advisory lock to prevent duplicate concurrent evaluation.
- Attachment uploads are bounded per file and by total workspace quota.
- Keep `LLM_ENABLED=false` until the local model endpoint has been explicitly validated.

## Prepare configuration

1. Copy `.env.production.example` to `.env.production`.
2. Generate independent random values for `POSTGRES_PASSWORD`, `JWT_SECRET`, and `METRICS_BEARER_TOKEN`.
3. Put the real external HTTPS origin in `CORS_ALLOW_ORIGINS`; `https://support.example.com` is not valid for public production.
4. Leave `BOOTSTRAP_ENABLED=false` for an initialized installation.
5. Keep `CSP_WEB_BIND=127.0.0.1:8180` when using the host tunnel/reverse proxy.
6. Set `CSP_BUILD_REVISION` to the deployed git commit SHA.
7. Review attachment quotas and scheduler interval for host capacity.

Do not commit `.env.production`.

## Validate before deploy

```bash
RELEASE_VERSION=0.9.0 bash tools/release-check.sh

POSTGRES_PASSWORD=replace-with-a-long-random-password \
CSP_ENV_FILE=.env.production.example \
docker compose -f compose.production.yml config --quiet

bash -n \
  tools/backup.sh \
  tools/restore-verify.sh \
  tools/release-check.sh \
  tools/smoke-production.sh \
  tools/deploy-production.sh \
  tools/production-edge-check.sh \
  tools/backup-offhost.sh \
  tools/backup-and-offhost.sh
```

## Deploy

The preferred production path is `.github/workflows/deploy-production.yml`, which runs only on the dedicated self-hosted production runner and invokes `tools/deploy-production.sh`.

The deployment script requires a clean checkout and mode-600 `.env.production`, records the git SHA, creates and checksums a PostgreSQL backup when an existing database is present, performs an isolated restore verification, deploys the stack, and runs production smoke checks.

Manual equivalent:

```bash
export CSP_ENV_FILE=.env.production
export RELEASE_VERSION=0.9.0
export CSP_BUILD_REVISION="$(git rev-parse HEAD)"
bash tools/deploy-production.sh
```

Confirm locally:

```bash
curl -fsS http://127.0.0.1:8180/health
curl -fsS http://127.0.0.1:8180/ready
CSP_SMOKE_BASE_URL=http://127.0.0.1:8180 RELEASE_VERSION=0.9.0 bash tools/smoke-production.sh
```

`/ready` requires PostgreSQL and Redis. `/docs`, `/openapi.json`, and `/redoc` must not be exposed through the production web edge. `/api/v1/metrics` without valid bearer credentials must not return metrics.

## Public edge

Public exposure is intentionally separate from the existing host tunnel stack. Follow `docs/production-edge-backup.md` and use the dedicated `cloudflared-support-endpoint.service` example rather than modifying another project's `cloudflared.service`.

Before declaring public production ready:

```bash
CSP_ENV_FILE=.env.production bash tools/production-edge-check.sh
```

The check fails closed for placeholder CORS origins, non-loopback CSP web binding, missing/invalid HTTPS endpoint, incorrect runtime version/build identity, exposed API documentation, or an edge that does not route to the expected application.

## Backup and recovery

Create and verify a local PostgreSQL backup:

```bash
CSP_ENV_FILE=.env.production bash tools/backup.sh
CSP_ENV_FILE=.env.production bash tools/restore-verify.sh backups/csp-YYYYMMDDTHHMMSSZ.dump
```

A backup on the application host is only a local recovery checkpoint. Disaster recovery requires an independent off-host destination. The repository provides `tools/backup-offhost.sh`, `tools/backup-and-offhost.sh`, and systemd service/timer examples. The off-host transfer verifies the local checksum before transport and verifies the remote copy again after transport.

Do not reuse unrelated host backup services or destinations unless they have been explicitly provisioned for this application.

## Rollback

Before a production schema change:

1. create a fresh backup;
2. complete isolated restore verification;
3. record the current deployed git SHA;
4. deploy the candidate;
5. run the smoke suite;
6. restore the previous source/image revision first if rollback is required;
7. perform a database downgrade only after explicit schema compatibility review.

## Stable v0.9.0 release criteria

Repository-level promotion requires:

- Python/Ruff/pytest/whitespace CI green;
- Alembic upgrade/downgrade CI green;
- React typecheck/build green;
- production compose and shell validation green;
- PostgreSQL backup/restore rehearsal green;
- release metadata/invariant consistency green;
- full hardened production compose smoke green;
- successful target-host deployment with backup/restore/smoke verification.

Public-production activation additionally requires:

- a dedicated real HTTPS hostname for Support Endpoint;
- `CORS_ALLOW_ORIGINS` set to that real origin;
- a dedicated tunnel/reverse-proxy route to `127.0.0.1:8180`;
- successful `tools/production-edge-check.sh` against the real HTTPS endpoint;
- an independent off-host backup destination with a successful verified transfer.

Until those environment-specific items are satisfied, the application may run privately on the production host but must not be described as fully public-production ready.
