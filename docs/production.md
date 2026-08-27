# Production deployment — v0.8.1-alpha

This runbook describes the hardened single-host deployment path for Support Endpoint. It is intentionally separate from the development compose file.

## Security invariants

- Use `compose.production.yml`, not `docker-compose.yml`, for external service.
- Keep the web listener on loopback by default (`127.0.0.1:8180`) and expose it through the host reverse proxy or tunnel.
- The API is not published on a host port in production; nginx reaches it over the private Docker backend network.
- The backend Docker network is `internal: true` and remains separate from AI-project-SRV networks and volumes.
- API and web containers use read-only root filesystems, `no-new-privileges`, and reduced Linux capabilities.
- FastAPI docs/OpenAPI are disabled when `APP_ENV=production`.
- Production startup fails if the JWT secret is unsafe, bootstrap is enabled, auth rate limiting is disabled, HSTS mode is disabled, CORS origins are empty, or the metrics bearer token is too short.
- Keep `LLM_ENABLED=false` until the local model endpoint has been explicitly validated. The LLM never becomes an execution authority.

## Prepare configuration

1. Copy `.env.production.example` to `.env.production`.
2. Generate independent random values for `POSTGRES_PASSWORD`, `JWT_SECRET`, and `METRICS_BEARER_TOKEN`.
3. Put the real external HTTPS origin in `CORS_ALLOW_ORIGINS`.
4. Leave `BOOTSTRAP_ENABLED=false` for an initialized installation.
5. Set `CSP_BUILD_REVISION` to the deployed git commit SHA.

Do not commit `.env.production`.

## Validate before deploy

```bash
POSTGRES_PASSWORD=validation-only \
CSP_ENV_FILE=.env.production.example \
docker compose -f compose.production.yml config --quiet

bash -n tools/backup.sh tools/restore-verify.sh
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
```

`/ready` requires both PostgreSQL and Redis. Optional advisory LLM availability does not affect readiness.

`/docs` and `/openapi.json` must not be available through the production web edge.

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

The command writes a mode-600 `.dump` plus `.sha256` under `backups/` by default. Copy backups off-host using your normal encrypted backup destination; a backup that exists only on the application host is not a disaster-recovery backup.

Verify a backup by restoring it into an isolated temporary database and dropping that database afterwards:

```bash
CSP_ENV_FILE=.env.production bash tools/restore-verify.sh backups/csp-YYYYMMDDTHHMMSSZ.dump
```

The verifier checks the checksum when present, performs `pg_restore --exit-on-error`, validates the schema marker, and never targets the production database name.

GitHub CI performs this full backup/restore rehearsal against an ephemeral PostgreSQL instance on every change to the branch/PR.

## Database performance

Phase 8B adds composite indexes for ticket workspace/status/assignee/client timelines, support-task timelines, user notification timelines, SLA deadlines and ticket audit status history. Alembic upgrade and downgrade remain CI-gated.

## Rollback

Application rollback is image/source revision rollback plus Alembic compatibility review. Do not automatically downgrade a production database without checking whether the target release supports the current schema. Take a fresh backup and complete a restore rehearsal before a production schema change.

## Remaining Phase 8 work

Runtime/edge hardening is Phase 8A. Phase 8B covers observability, hot-path indexes and tested PostgreSQL backup/restore. Before final production sign-off, Phase 8 still needs browser-session hardening, scheduler reliability, backup retention/off-host policy, distributed AI breaker evaluation if multiple API workers are introduced, and final security review.
