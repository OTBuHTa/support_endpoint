# Production deployment — v0.9.0-rc1

This runbook describes the hardened single-host deployment path for Support Endpoint. It is intentionally separate from the development compose file.

## Security invariants

- Use `compose.production.yml`, not the development compose file, for external service.
- Keep the web listener on loopback by default (`127.0.0.1:8180`) and expose it through the host reverse proxy or tunnel.
- The API is not published on a host port in production; nginx reaches it over the private Docker backend network.
- The backend Docker network is `internal: true` and remains separate from AI-project-SRV networks and volumes.
- API, scheduler and web containers use read-only root filesystems where applicable, `no-new-privileges`, and reduced Linux capabilities.
- FastAPI docs/OpenAPI are disabled when `APP_ENV=production`.
- Production startup fails if the JWT secret is unsafe, bootstrap is enabled, auth rate limiting is disabled, HSTS mode is disabled, CORS origins are empty, the metrics bearer token is too short, or the SLA scheduler interval is unsafe.
- Browser refresh sessions use an HttpOnly, SameSite=Strict cookie with server-side rotation/revocation; refresh tokens are not persisted in JavaScript storage.
- The SLA scheduler is a separate process and uses a PostgreSQL advisory lock to prevent duplicate concurrent evaluation.
- Attachment uploads are bounded per file and by total workspace quota; quota allocation is serialized to prevent concurrent over-allocation.
- Keep `LLM_ENABLED=false` until the local model endpoint has been explicitly validated. The LLM never becomes an execution authority, and its circuit state is shared through Redis with a local fail-safe fallback.

## Prepare configuration

1. Copy `.env.production.example` to `.env.production`.
2. Generate independent random values for `POSTGRES_PASSWORD`, `JWT_SECRET`, and `METRICS_BEARER_TOKEN`.
3. Put the real external HTTPS origin in `CORS_ALLOW_ORIGINS`.
4. Leave `BOOTSTRAP_ENABLED=false` for an initialized installation.
5. Set `CSP_BUILD_REVISION` to the deployed git commit SHA.
6. Review `ATTACHMENT_MAX_BYTES`, `ATTACHMENT_WORKSPACE_QUOTA_BYTES`, and `SLA_SCHEDULER_INTERVAL_SECONDS` for the host capacity and operating policy.

Do not commit `.env.production`.

## Validate before deploy

```bash
RELEASE_VERSION=0.9.0-rc1 bash tools/release-check.sh

POSTGRES_PASSWORD=replace-with-a-long-random-password \
CSP_ENV_FILE=.env.production.example \
docker compose -f compose.production.yml config --quiet

bash -n tools/backup.sh tools/restore-verify.sh tools/release-check.sh tools/smoke-production.sh
```

Then validate the real environment by starting the migration/API path locally or on the target host. Unsafe production settings fail during application import before the API starts accepting traffic.

## Deploy

```bash
export CSP_ENV_FILE=.env.production
export CSP_BUILD_REVISION="$(git rev-parse HEAD)"
docker compose -f compose.production.yml up -d --build
```

The migration service must complete successfully before the API starts. Confirm:

```bash
curl -fsS http://127.0.0.1:8180/health
curl -fsS http://127.0.0.1:8180/ready
CSP_SMOKE_BASE_URL=http://127.0.0.1:8180 bash tools/smoke-production.sh
```

`/ready` requires both PostgreSQL and Redis. Optional advisory LLM availability does not affect readiness.

`/docs` and `/openapi.json` must not be available through the production web edge. `/api/v1/metrics` without valid bearer credentials must not return metrics.

## Metrics and logs

The API emits JSON logs with correlation ID and selected structured fields. Completed requests include method, path, status code and duration in milliseconds. Request bodies, authorization headers and token values are intentionally not logged.

Prometheus-format metrics are available at `/api/v1/metrics` only when `METRICS_BEARER_TOKEN` is configured. Use:

```bash
curl -fsS \
  -H "Authorization: Bearer $METRICS_BEARER_TOKEN" \
  http://127.0.0.1:8180/api/v1/metrics
```

The endpoint returns 404 when metrics are not configured and 401 for invalid credentials.

## Backup and restore rehearsal

Attachments are currently stored inside PostgreSQL, so the database dump covers ticket data, communications, attachment bytes, RBAC, sessions, SLA state and audit records.

Create a checksummed custom-format PostgreSQL backup:

```bash
CSP_ENV_FILE=.env.production bash tools/backup.sh
```

The command writes a mode-600 `.dump` plus `.sha256` under `backups/` by default. Copy backups off-host using an encrypted backup destination; a backup that exists only on the application host is not a disaster-recovery backup.

Verify a backup by restoring it into an isolated temporary database and dropping that database afterwards:

```bash
CSP_ENV_FILE=.env.production bash tools/restore-verify.sh backups/csp-YYYYMMDDTHHMMSSZ.dump
```

The verifier checks the checksum when present, performs `pg_restore --exit-on-error`, validates the schema marker, and never targets the production database name.

GitHub CI performs this full backup/restore rehearsal against an ephemeral PostgreSQL instance on every branch/PR change.

## Database and storage

Composite indexes cover ticket workspace/status/assignee/client timelines, support-task timelines, user notification timelines, SLA deadlines and ticket audit status history. Alembic upgrade and downgrade remain CI-gated.

Attachments are still PostgreSQL-backed in RC1. `ATTACHMENT_MAX_BYTES` bounds a single upload and `ATTACHMENT_WORKSPACE_QUOTA_BYTES` bounds aggregate workspace attachment bytes. For larger installations, migration to object storage remains an architectural scaling option rather than a release blocker for the bounded single-host profile.

## Rollback

Application rollback is image/source revision rollback plus Alembic compatibility review. Do not automatically downgrade a production database without checking whether the target release supports the current schema.

Before a production schema change:

1. create a fresh backup;
2. complete an isolated restore rehearsal;
3. record the currently deployed git SHA;
4. deploy the candidate;
5. run `tools/smoke-production.sh`;
6. if application rollback is required, restore the previous source/image revision first and only perform a database downgrade when explicitly verified safe for that schema transition.

## RC1 release criteria

`v0.9.0-rc1` is acceptable for production-like deployment only when all of the following hold:

- Python/Ruff/pytest/whitespace CI is green;
- Alembic full upgrade/downgrade CI is green;
- React typecheck/build is green;
- production compose and shell validation are green;
- PostgreSQL backup/restore rehearsal is green;
- release metadata/invariant check is green;
- full hardened compose stack starts successfully and `tools/smoke-production.sh` passes;
- target-host secrets, HTTPS origin, reverse proxy/tunnel and off-host backup destination are configured outside the repository.

Environment-specific external DNS/TLS/reverse-proxy checks are deployment responsibilities and are intentionally not simulated by repository CI.
