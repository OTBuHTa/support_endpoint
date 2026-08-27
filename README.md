# Customer Service Platform

Production-oriented CRM / Service Desk platform for remote customer support: tickets, operator queues, communications, knowledge base, deterministic operations and optional advisory AI assistance via a shared local LLM.

Operationally independent from **AI-project-SRV**, which runs on the same host (`srv-ai`) but does not share any database, cache, network, volume or secret with this project.

## Current milestone

`v0.7.0-alpha` — **Phase 7B: Client Identity + Customer Portal** on top of the completed operator Control Center.

## Architecture principles

- Own Postgres database (`csp`), own Redis, own Docker network/volumes — never shared with AI-project-SRV.
- Workspace isolation and deny-by-default RBAC remain authoritative for operator endpoints.
- Customer portal authorization is ownership-based, not workspace-role based: an authenticated User must have an explicit `ClientUserLink` to a CRM Client.
- Customer users do not need a WorkspaceMembership and therefore do not inherit operator permissions.
- Portal APIs derive workspace/client scope from the authenticated link and never accept arbitrary client IDs from the browser.
- Internal notes are physically separate from customer-visible messages and are not exposed through portal APIs.
- Tasks, SLA state and notifications are deterministic application records; AI cannot execute them.
- AI assistance is advisory only and neither frontend calls the LLM directly.

## Implemented

- **Foundation (Phase 2):** FastAPI, PostgreSQL/Redis, health/readiness, Alembic, users/workspaces/memberships, JWT + rotating refresh sessions, deny-by-default RBAC, auth rate limiting, append-only audit events, structured logging and correlation IDs.
- **CRM (Phase 3):** organizations, clients and contacts with workspace-scoped CRUD, search, pagination, soft-delete and IDOR guards (ADR-004).
- **Service Desk (Phase 4):** ticket lifecycle, queues/categories/tags, assignment history, filtering, separate `tickets.close` permission and audit (ADR-005).
- **Communications (Phase 5):** conversations, channel abstraction, inbound/outbound messages, separate internal notes and bounded binary attachments (ADR-006).
- **Knowledge + Advisory AI (Phase 6A):** knowledge articles, AI permissions, redaction, immutable suggestions, rate limit and process-local circuit breaker (ADR-007).
- **Deterministic Operations (Phase 6B):** ticket tasks, per-priority SLA policies, replayable ticket SLA clocks, warning/breach evaluation and user-scoped notifications (ADR-008).
- **Operator Control Center (Phase 7A):** React 18 + Vite + TypeScript operator UI, workspace selection, permission-aware navigation and frontend CI (ADR-009).
- **Client Portal (Phase 7B):** explicit User↔Client binding, ownership-scoped portal accounts/tickets/messages, customer ticket creation and inbound replies, cross-user IDOR regressions, and a separate `/portal.html` Vite entrypoint (ADR-010).

AI remains disabled by default with `LLM_ENABLED=false`. When disabled, rate-limited, circuit-open or otherwise unavailable, the non-AI product remains operational.

## Quick start

1. Copy `.env.example` to `.env` and replace `JWT_SECRET`.
2. Run `docker compose up --build -d` (or `make up`).
3. Run `docker compose --profile tools run --rm --build migration` (or `make migrate`).
4. Open `http://localhost:8180` for the operator UI, `http://localhost:8180/portal.html` for the customer portal, or `http://localhost:8100/docs` for the API.
5. Call `POST /api/v1/auth/bootstrap` once to create the initial owner/workspace if this is a fresh install.
6. A customer first registers a normal User account; an authorized operator explicitly links that login to the intended Client record with the portal-link endpoint.
7. Set `BOOTSTRAP_ENABLED=false` after initialization before external exposure.
8. Keep `LLM_ENABLED=false` until the local model endpoint is intentionally enabled and validated.

## Ports (`srv-ai`)

| Service | Host port | Notes |
|---|---|---|
| api | 8100 → 8000 | Does not collide with AI-project-SRV's 8000/8080 |
| web | 8180 → 80 | Operator + customer Vite bundles served by nginx |

Docker network subnet: `172.31.0.0/24` (distinct from AI-project-SRV's `172.30.0.0/29`).

## Testing

```bash
cd apps/api
pytest -q
ruff check app tests

cd ../web
npm ci --no-audit --no-fund
npm run typecheck
npm run build
```

GitHub Actions validates Python 3.12 lint/tests, whitespace, complete Alembic upgrade/downgrade, React TypeScript typecheck and multi-entry production Vite build.

## Roadmap

See `docs/architecture.md`. Phase 7 is complete after the operator console and ownership-scoped customer portal. Phase 8 performs production hardening: security review, browser-session hardening, observability/performance, scheduler/deployment work, distributed breaker evaluation, storage evaluation and final release documentation.
