# Customer Service Platform

Production-oriented CRM / Service Desk platform for remote customer support: tickets, operator queues, communications, knowledge base, deterministic operations and optional advisory AI assistance via a shared local LLM.

Operationally independent from **AI-project-SRV**, which runs on the same host (`srv-ai`) but does not share any database, cache, network, volume, secret, scheduler or attachment storage with this project.

## Current milestone

`v0.9.0-rc1` — **Release Candidate 1: production-readiness validation**. New product features are frozen for this candidate; changes are limited to release consistency, deployment/smoke gates, security findings and release documentation.

## Architecture principles

- Own Postgres database (`csp`), own Redis, own Docker network/volumes — never shared with AI-project-SRV.
- Workspace isolation and deny-by-default RBAC remain authoritative for operator endpoints.
- Customer portal authorization is ownership-based, not workspace-role based: an authenticated User must have an explicit `ClientUserLink` to a CRM Client.
- Customer users do not need a WorkspaceMembership and therefore do not inherit operator permissions.
- Portal APIs derive workspace/client scope from the authenticated link and never accept arbitrary client IDs from the browser.
- Internal notes are physically separate from customer-visible messages and are not exposed through portal APIs.
- Tasks, SLA state and notifications are deterministic application records; AI cannot execute them.
- AI assistance is advisory only and neither frontend calls the LLM directly.
- Production configuration fails closed and the API is not directly exposed on a host port.

## Implemented

- **Foundation (Phase 2):** FastAPI, PostgreSQL/Redis, health/readiness, Alembic, users/workspaces/memberships, JWT + rotating refresh sessions, deny-by-default RBAC, auth rate limiting, append-only audit events, structured logging and correlation IDs.
- **CRM (Phase 3):** organizations, clients and contacts with workspace-scoped CRUD, search, pagination, soft-delete and IDOR guards (ADR-004).
- **Service Desk (Phase 4):** ticket lifecycle, queues/categories/tags, assignment history, filtering, separate `tickets.close` permission and audit (ADR-005).
- **Communications (Phase 5):** conversations, channel abstraction, inbound/outbound messages, separate internal notes and bounded binary attachments (ADR-006).
- **Knowledge + Advisory AI (Phase 6A):** knowledge articles, AI permissions, redaction, immutable suggestions and rate limiting (ADR-007).
- **Deterministic Operations (Phase 6B):** ticket tasks, per-priority SLA policies, replayable ticket SLA clocks, warning/breach evaluation and user-scoped notifications (ADR-008).
- **Operator Control Center (Phase 7A):** React 18 + Vite + TypeScript operator UI, workspace selection, permission-aware navigation and frontend CI (ADR-009).
- **Client Portal (Phase 7B):** explicit User↔Client binding, ownership-scoped portal accounts/tickets/messages, customer ticket creation and inbound replies, cross-user IDOR regressions, and a separate `/portal.html` Vite entrypoint (ADR-010).
- **Runtime & Edge Hardening (Phase 8A):** production fail-closed settings, private backend network, no direct API host port, read-only application containers, reduced capabilities, production security headers, disabled API docs and production manifest CI.
- **Observability & Recovery (Phase 8B):** protected Prometheus-format request metrics, structured request completion logs, PostgreSQL + Redis readiness, composite hot-path indexes, checksummed database backups and CI-tested isolated restore rehearsal.
- **Browser Sessions & Scheduler (Phase 8C):** HttpOnly/SameSite refresh-cookie browser flow, refresh rotation/revocation and autonomous SLA scheduler with PostgreSQL advisory locking.
- **Final Security Hardening (Phase 8D):** Redis-backed distributed AI circuit breaker with local fail-safe fallback, configurable attachment limits, per-workspace storage quota, serialized quota enforcement and filename normalization.
- **Release Candidate 1 (v0.9.0-rc1):** synchronized release metadata, machine-checkable release invariants and production-stack smoke validation.

AI remains disabled by default with `LLM_ENABLED=false`. When disabled, rate-limited, circuit-open or otherwise unavailable, the non-AI product remains operational.

## Development quick start

1. Copy `.env.example` to `.env` and replace `JWT_SECRET`.
2. Run `docker compose up --build -d` (or `make up`).
3. Run `docker compose --profile tools run --rm --build migration` (or `make migrate`).
4. Open `http://localhost:8180` for the operator UI, `http://localhost:8180/portal.html` for the customer portal, or `http://localhost:8100/docs` for the development API.
5. Call `POST /api/v1/auth/bootstrap` once to create the initial owner/workspace if this is a fresh install.
6. A customer first registers a normal User account; an authorized operator explicitly links that login to the intended Client record with the portal-link endpoint.
7. Set `BOOTSTRAP_ENABLED=false` after initialization before external exposure.
8. Keep `LLM_ENABLED=false` until the local model endpoint is intentionally enabled and validated.

For production, use `.env.production`, `compose.production.yml`, and `docs/production.md`; do not use the development port exposure as the external deployment model.

## Development ports (`srv-ai`)

| Service | Host port | Notes |
|---|---|---|
| api | 8100 → 8000 | Development only; production does not publish the API port |
| web | 8180 → 80 | Operator + customer Vite bundles served by nginx |

Docker network subnet: `172.31.0.0/24` (distinct from AI-project-SRV's `172.30.0.0/29`).

## Testing

```bash
cd apps/api
pytest -q
ruff check app tests

cd ../web
npm install --no-audit --no-fund
npm run typecheck
npm run build

cd ../..
RELEASE_VERSION=0.9.0-rc1 bash tools/release-check.sh
POSTGRES_PASSWORD=replace-with-a-long-random-password \
CSP_ENV_FILE=.env.production.example \
docker compose -f compose.production.yml config --quiet
```

GitHub Actions validates Python 3.12 lint/tests, whitespace, complete Alembic upgrade/downgrade, React TypeScript typecheck/build, the production compose manifest, shell syntax, a real PostgreSQL backup/restore rehearsal, RC release consistency and a hardened production-stack smoke test.

## Release policy

`v0.9.0-rc1` is a release candidate, not the final production tag. No new feature work is accepted into the RC branch. A production release requires the complete CI matrix to remain green, a successful production-like deployment using `compose.production.yml`, backup/restore verification, smoke checks, and review of any environment-specific deployment findings.

See `docs/architecture.md` and `docs/production.md` for architecture and deployment details.
