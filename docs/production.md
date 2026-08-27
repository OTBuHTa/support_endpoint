# Production deployment — v0.8.0-alpha

This runbook describes the hardened single-host deployment path for Support Endpoint. It is intentionally separate from the development compose file.

## Security invariants

- Use `compose.production.yml`, not `docker-compose.yml`, for external service.
- Keep the web listener on loopback by default (`127.0.0.1:8180`) and expose it through the host reverse proxy or tunnel.
- The API is not published on a host port in production; nginx reaches it over the private Docker backend network.
- The backend Docker network is `internal: true` and remains separate from AI-project-SRV networks and volumes.
- API and web containers use read-only root filesystems, `no-new-privileges`, and reduced Linux capabilities.
- FastAPI docs/OpenAPI are disabled when `APP_ENV=production`.
- Production startup fails if the JWT secret is unsafe, bootstrap is enabled, auth rate limiting is disabled, HSTS mode is disabled, or CORS origins are empty.
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

`/docs` and `/openapi.json` must not be available through the production web edge.

## Rollback

Application rollback is image/source revision rollback plus Alembic compatibility review. Do not automatically downgrade a production database without checking whether the target release supports the current schema. Database backups and restore rehearsal are required before final production sign-off.

## Remaining Phase 8 work

Runtime/edge hardening is Phase 8A. Before a final production release, Phase 8 must still complete observability/metrics review, database/index performance review, persistent attachment storage/backup strategy, scheduler reliability, browser-session hardening, restore rehearsal, and final security review.
