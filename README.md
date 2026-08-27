# Customer Service Platform

Production-oriented CRM / Service Desk platform for remote customer support: tickets, operator queues, communications, SLA, knowledge base, and optional advisory AI assistance via a shared local LLM.

Operationally independent from **AI-project-SRV**, which runs on the same host (`srv-ai`) but does not share any database, cache, network, volume, or secret with this project.

## Current milestone

`v0.3.0-alpha` — Foundation + CRM + Service Desk + Communications: authentication, workspace/multi-tenancy model, deny-by-default RBAC, audit trail, CRM, ticket lifecycle, conversations/messages, isolated internal notes, and bounded attachments.

## Architecture principles

- Own Postgres database (`csp`), own Redis, own Docker network/volumes — never shared with AI-project-SRV.
- Workspace (tenant) isolation is a first-class requirement; every tenant-scoped endpoint performs an object-level authorization check.
- Backend permissions are authoritative; roles are convenience bundles.
- Internal notes are physically separate from customer-visible messages; message APIs cannot accidentally serialize operator-only notes.
- AI assistance (Phase 6+) is advisory only — never performs mutating actions directly; deterministic application logic always mediates.
- The frontend never calls the LLM directly.

## Implemented

- **Foundation (Phase 2):** FastAPI, PostgreSQL/Redis, health/readiness, Alembic, users/workspaces/memberships, JWT + rotating refresh sessions, deny-by-default RBAC, auth rate limiting, append-only audit events, structured logging and correlation IDs.
- **CRM (Phase 3):** `ClientOrganization`, `Client`, `ClientContact` — workspace-scoped CRUD, case-insensitive search, pagination, soft-delete and IDOR guards (ADR-004).
- **Service Desk (Phase 4):** `Ticket`, server-controlled lifecycle, `Queue`/`TicketCategory`/`Tag`, assignment history, search/filtering, separate `tickets.close` permission and IDOR guards (ADR-005).
- **Communications (Phase 5):** ticket-scoped `Conversation` channel abstraction (`web`, `email`, `chat`, `phone`, `api`), inbound/outbound `Message`, separate `InternalNote`, binary `Attachment` with 5 MiB cap and SHA-256 integrity metadata, audit events and workspace/ticket/object authorization (ADR-006).

Phase 5 records communications but does **not** send or poll external email/chat providers. External channel adapters remain later work and must call the deterministic service layer.

## Quick start

1. Copy `.env.example` to `.env` and replace `JWT_SECRET`.
2. Run `docker compose up --build -d` (or `make up`).
3. Run `docker compose --profile tools run --rm --build migration` (or `make migrate`).
4. Open `http://localhost:8100/docs` (API) or `http://localhost:8180` (placeholder web UI).
5. Call `POST /api/v1/auth/bootstrap` once to create the initial owner/workspace.
6. Set `BOOTSTRAP_ENABLED=false` after initialization before external exposure.

## Ports (`srv-ai`)

| Service | Host port | Notes |
|---|---|---|
| api | 8100 → 8000 | Does not collide with AI-project-SRV's 8000/8080 |
| web | 8180 → 80 | Placeholder page; real UI in Phase 7 |

Docker network subnet: `172.31.0.0/24` (distinct from AI-project-SRV's `172.30.0.0/29`).

## Testing

```bash
cd apps/api
pytest -q
ruff check app tests
```

Security regressions cover workspace isolation, object-level IDOR, role boundaries, ticket state transitions, communications separation, cross-workspace conversation denial and attachment size/integrity behavior. GitHub Actions also performs an Alembic upgrade/downgrade check on Python 3.12.

## Roadmap

See `docs/architecture.md` for the full phase plan. Next milestone: **Phase 6 — Operations + AI** (tasks, SLA, notifications, knowledge base and bounded/advisory local-LLM features).
