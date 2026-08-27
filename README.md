# Customer Service Platform

Production-oriented CRM / Service Desk platform for remote customer
support: tickets, operator queues, SLA, knowledge base, and optional
advisory AI assistance via a shared local LLM.

Operationally independent from **AI-project-SRV**, which runs on the
same host (`srv-ai`) but does not share any database, cache, network,
volume, or secret with this project.

## Current milestone

`v0.1.0-alpha` — Foundation + CRM + Service Desk: authentication,
workspace/multi-tenancy model, RBAC with deny-by-default authorization,
health/readiness, structured logging, audit trail, client/organization/
contact records, and tickets with a server-controlled lifecycle.

## Architecture principles

- Own Postgres database (`csp`), own Redis, own Docker network/volumes
  — never shared with AI-project-SRV.
- Workspace (tenant) isolation is a first-class requirement; every
  tenant-scoped endpoint performs an object-level authorization check.
- Backend permissions are authoritative; roles are convenience bundles.
- AI assistance (Phase 6+) is advisory only — never performs mutating
  actions directly; deterministic application logic always mediates.
- The frontend never calls the LLM directly.

## Implemented (Foundation)

- FastAPI service foundation, PostgreSQL + Redis via Docker Compose.
- Health and readiness endpoints.
- Alembic migration baseline.
- User / Workspace / WorkspaceMembership / Role / Permission /
  RolePermission models.
- System roles: Client, Operator, Supervisor, Administrator, with
  canonical permission bundles.
- One-time bootstrap-owner flow, plus self-service registration.
- JWT access tokens and rotating, revocable opaque refresh sessions.
- Deny-by-default, object-level workspace authorization
  (`require_permission`), returning 404 (not 403) on both "no
  membership" and "no permission" to avoid disclosing workspace
  existence to non-members.
- Redis-backed auth rate limiting (fails open if Redis is down).
- Hash-chained-style append-only audit event log.
- Structured JSON logging with request correlation IDs.
- **CRM (Phase 3):** `ClientOrganization`, `Client`, `ClientContact` —
  workspace-scoped CRUD, case-insensitive search (`?q=`), pagination,
  organization filtering, soft-delete, object-level IDOR guard on
  every by-id lookup (see ADR-004).
- **Service Desk (Phase 4):** `Ticket` with a server-controlled state
  machine (`new → open → in_progress → waiting_customer/internal →
  resolved → closed`, reopen supported — see ADR-005),
  `Queue`/`TicketCategory`/`Tag` workspace-customizable lookups,
  assignment with workspace-membership validation and append-only
  history (`GET /tickets/{id}/assignments`), filtered search
  (status/priority/queue/category/assignee/client/`?q=`), pagination,
  `tickets.close` enforced as a distinct permission from
  `tickets.update`.

## Quick start

1. Copy `.env.example` to `.env` and replace `JWT_SECRET`.
2. Run `docker compose up --build -d` (or `make up`).
3. Run `docker compose --profile tools run --rm --build migration` (or `make migrate`).
4. Open `http://localhost:8100/docs` (API) or `http://localhost:8180` (placeholder web UI).
5. Call `POST /api/v1/auth/bootstrap` once to create the initial owner/workspace.
6. Set `BOOTSTRAP_ENABLED=false` after initialization before external exposure.

## Ports (this host, `srv-ai`)

| Service | Host port | Notes |
|---|---|---|
| api | 8100 → 8000 | Does not collide with AI-project-SRV's 8000/8080 |
| web | 8180 → 80 | Placeholder page; real UI in Phase 7 |

Docker network subnet: `172.31.0.0/24` (distinct from AI-project-SRV's `172.30.0.0/29`).

## Testing

```
cd apps/api
pytest -q          # 37 tests, including mandatory security regressions:
                    #  - workspace A cannot access workspace B (workspaces, clients, tickets)
                    #  - a user with no membership cannot access a workspace
                    #  - an Operator cannot reach an Administrator-only endpoint
                    #  - an Operator can read but not write clients (RBAC)
                    #  - an Operator can update but not close a ticket (tickets.close)
                    #  - the Client system role has zero internal CRM/Service-Desk access
                    #  - a client/ticket id from one workspace never resolves via another
                    #    workspace's path (object-level IDOR guard)
                    #  - a revoked/reused refresh token is rejected
                    #  - an invalid ticket status transition is rejected server-side
ruff check app tests
```

## Roadmap

See `docs/architecture.md` for the full phase plan (CRM, Service Desk,
Communications, SLA/AI, Frontend, Production hardening).
