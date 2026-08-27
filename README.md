# Customer Service Platform

Production-oriented CRM / Service Desk platform for remote customer support: tickets, operator queues, communications, knowledge base, deterministic operations and optional advisory AI assistance via a shared local LLM.

Operationally independent from **AI-project-SRV**, which runs on the same host (`srv-ai`) but does not share any database, cache, network, volume or secret with this project.

## Current milestone

`v0.6.0-alpha` — **Phase 7A: Operator Control Center**. The nginx placeholder has been replaced by a real React/Vite/TypeScript web application over the established backend contracts.

## Architecture principles

- Own Postgres database (`csp`), own Redis, own Docker network/volumes — never shared with AI-project-SRV.
- Workspace isolation and deny-by-default RBAC remain authoritative at every tenant-scoped endpoint.
- The frontend reads `/workspaces/{id}/my-permissions` and hides unavailable surfaces, but backend authorization remains authoritative.
- Internal notes are physically separate from customer-visible messages.
- Tasks, SLA state and notifications are deterministic application records; AI cannot execute them.
- AI assistance is advisory only and the frontend never calls the LLM directly.

## Implemented

- **Foundation (Phase 2):** FastAPI, PostgreSQL/Redis, health/readiness, Alembic, users/workspaces/memberships, JWT + rotating refresh sessions, deny-by-default RBAC, auth rate limiting, append-only audit events, structured logging and correlation IDs.
- **CRM (Phase 3):** organizations, clients and contacts with workspace-scoped CRUD, search, pagination, soft-delete and IDOR guards (ADR-004).
- **Service Desk (Phase 4):** ticket lifecycle, queues/categories/tags, assignment history, filtering, separate `tickets.close` permission and audit (ADR-005).
- **Communications (Phase 5):** conversations, channel abstraction, inbound/outbound messages, separate internal notes and bounded binary attachments (ADR-006).
- **Knowledge + Advisory AI (Phase 6A):** knowledge articles, AI permissions, redaction, immutable suggestions, rate limit and process-local circuit breaker (ADR-007).
- **Deterministic Operations (Phase 6B):** ticket tasks, per-priority SLA policies, replayable ticket SLA clocks, warning/breach evaluation and user-scoped notifications (ADR-008).
- **Operator Control Center (Phase 7A):** React 18 + Vite + TypeScript, operator login/token refresh, workspace selection, permission-aware navigation, Overview, Tickets, Clients, Tasks, Knowledge and Notifications, responsive dark UI, nginx `/api` proxy and frontend CI.

AI remains disabled by default with `LLM_ENABLED=false`. When disabled, rate-limited, circuit-open or otherwise unavailable, the non-AI product remains operational.

## Quick start

1. Copy `.env.example` to `.env` and replace `JWT_SECRET`.
2. Run `docker compose up --build -d` (or `make up`).
3. Run `docker compose --profile tools run --rm --build migration` (or `make migrate`).
4. Open `http://localhost:8180` for the operator web UI or `http://localhost:8100/docs` for the API.
5. Call `POST /api/v1/auth/bootstrap` once to create the initial owner/workspace if this is a fresh install.
6. Set `BOOTSTRAP_ENABLED=false` after initialization before external exposure.
7. Keep `LLM_ENABLED=false` until the local model endpoint is intentionally enabled and validated.

## Ports (`srv-ai`)

| Service | Host port | Notes |
|---|---|---|
| api | 8100 → 8000 | Does not collide with AI-project-SRV's 8000/8080 |
| web | 8180 → 80 | React/Vite production bundle served by nginx |

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
```

GitHub Actions validates Python 3.12 lint/tests, whitespace, complete Alembic upgrade/downgrade, React TypeScript typecheck and production Vite build.

## Phase 7B — client portal identity boundary

A customer-facing portal is intentionally **not** simulated by reusing operator permissions. The current backend has workspace users and CRM Client records but no authoritative `User ↔ Client` binding. Phase 7B will add that identity contract, ownership-scoped portal endpoints and regressions before exposing customer tickets/messages in the browser. This prevents an attractive UI from becoming an authorization bypass.

## Roadmap

See `docs/architecture.md`. Phase 7B completes the customer portal identity/API boundary and portal UI. Phase 8 then performs production hardening, observability/performance work and final security review.
