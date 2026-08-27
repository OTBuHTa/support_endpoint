# Customer Service Platform

Production-oriented CRM / Service Desk platform for remote customer support: tickets, operator queues, communications, knowledge base, deterministic operations and optional advisory AI assistance via a shared local LLM.

Operationally independent from **AI-project-SRV**, which runs on the same host (`srv-ai`) but does not share any database, cache, network, volume or secret with this project.

## Current milestone

`v0.5.0-alpha` — **Phase 6B: Deterministic Operations** on top of the completed Foundation, CRM, Service Desk, Communications and Phase 6A Knowledge/AI layers.

## Architecture principles

- Own Postgres database (`csp`), own Redis, own Docker network/volumes — never shared with AI-project-SRV.
- Workspace isolation and deny-by-default RBAC remain authoritative at every tenant-scoped endpoint.
- Internal notes are physically separate from customer-visible messages.
- Tasks, SLA state and notifications are deterministic application records; AI cannot execute them.
- SLA first-response/resolution timestamps are reconstructed from customer-visible outbound messages and audited ticket status transitions.
- AI assistance is advisory only: it returns stored proposals and has no mutation, shell, infrastructure or external-message tools.
- The backend redacts email and phone-like values before sending ticket context to the LLM endpoint.
- LLM calls are bounded by a workspace usage limit and a process-local failure circuit breaker.
- The frontend never calls the LLM directly.

## Implemented

- **Foundation (Phase 2):** FastAPI, PostgreSQL/Redis, health/readiness, Alembic, users/workspaces/memberships, JWT + rotating refresh sessions, deny-by-default RBAC, auth rate limiting, append-only audit events, structured logging and correlation IDs.
- **CRM (Phase 3):** organizations, clients and contacts with workspace-scoped CRUD, search, pagination, soft-delete and IDOR guards (ADR-004).
- **Service Desk (Phase 4):** ticket lifecycle, queues/categories/tags, assignment history, filtering, separate `tickets.close` permission and audit (ADR-005).
- **Communications (Phase 5):** conversations, channel abstraction, inbound/outbound messages, separate internal notes and bounded binary attachments (ADR-006).
- **Knowledge + Advisory AI (Phase 6A):** workspace knowledge articles, `knowledge.read` / `knowledge.write`, `ai.assist`, immutable AI suggestions, prompt redaction, bounded knowledge context, per-workspace suggestion rate limit, process-local circuit breaker and OpenAI-compatible local `LLMGateway` (ADR-007).
- **Deterministic Operations (Phase 6B):** ticket tasks, per-priority SLA policies, replayable ticket SLA clocks, warning/breach evaluation, user-scoped in-app notifications and new deny-by-default operations permissions (ADR-008).

AI remains disabled by default with `LLM_ENABLED=false`. When disabled, rate-limited, circuit-open or otherwise unavailable, CRM/ticket/communications/knowledge/operations flows continue normally.

## Quick start

1. Copy `.env.example` to `.env` and replace `JWT_SECRET`.
2. Run `docker compose up --build -d` (or `make up`).
3. Run `docker compose --profile tools run --rm --build migration` (or `make migrate`).
4. Open `http://localhost:8100/docs` (API) or `http://localhost:8180` (placeholder web UI).
5. Call `POST /api/v1/auth/bootstrap` once to create the initial owner/workspace.
6. Set `BOOTSTRAP_ENABLED=false` after initialization before external exposure.
7. Keep `LLM_ENABLED=false` until the local model endpoint is intentionally enabled and validated.
8. A scheduler may periodically call the protected SLA evaluation service; missed ticks do not lose response/resolution history.

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

GitHub Actions validates Python 3.12 lint/tests, whitespace and complete Alembic upgrade/downgrade. Security regressions cover workspace/IDOR boundaries, RBAC, communications separation, attachment behavior, AI boundaries, task isolation, SLA history derivation, duplicate-safe breach notification and notification ownership.

## Roadmap

See `docs/architecture.md`. The next major checkpoint is **Phase 7 — Frontend**: React/Vite operator UI and client portal over the now-established CRM, Service Desk, Communications, Knowledge/AI and Operations contracts. Phase 8 then performs production hardening, observability/performance work and final security review.
