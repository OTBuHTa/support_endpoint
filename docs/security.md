# Security

This document covers the security controls implemented in Foundation
(Phase 2). Later phases (CRM, Service Desk, Communications, AI) must
extend — not weaken — these guarantees, and should add an equivalent
regression test for every new tenant-scoped endpoint.

## Authentication

- Passwords hashed with `bcrypt` (see ADR-002 for why not `passlib`).
  Inputs are truncated to bcrypt's 72-byte limit *before* hashing, on
  both hash and verify paths, so truncation is symmetric and never
  silently rejects a correct password or accepts a wrong one.
- Access tokens: JWT (HS256), 15-minute default lifetime, `sub` claim
  only (no roles/permissions embedded — always re-checked live).
- Refresh tokens: opaque random values; only a SHA-256 hash is ever
  persisted; rotated (old one revoked) on every use; reuse of an
  already-rotated token is rejected.
- `JWT_SECRET` has no safe default — the shipped `.env.example` value
  is an explicit placeholder string that must be replaced with at
  least 32 random bytes before any external exposure.

## Authorization

- Deny-by-default: an endpoint requiring a permission uses
  `require_permission(code)`; absence of a `RolePermission` grant
  denies the request.
- Object-level check on every workspace-scoped endpoint via
  `get_workspace_membership` — see ADR-003 for why this (and
  `require_permission`) return 404 rather than 403 on denial.
- Roles are convenience bundles (`Client`, `Operator`, `Supervisor`,
  `Administrator`); the backend never authorizes against a role name,
  only against the flattened permission-code set.
- Every tenant-scoped resource repository (`Client`, `ClientOrganization`,
  `ClientContact`, `Ticket`, `Queue`, `TicketCategory`, `Tag` as of
  Phase 4) filters by `(workspace_id, id)` together on every by-id
  lookup — not just workspace membership on the path — so a resource
  id belonging to a different workspace can never resolve through the
  wrong workspace's path, even for a legitimate member of that path's
  workspace. See ADR-004/ADR-005 and
  `test_client_id_from_one_workspace_not_resolvable_via_another_workspace_path`
  / `test_ticket_id_from_one_workspace_not_resolvable_via_another_workspace_path`.
- `tickets.close` is checked as an *additional* requirement on top of
  `tickets.update` specifically when transitioning a ticket to
  `CLOSED` (see ADR-005) — a permission dependency alone can only
  gate a whole endpoint, not a conditional target value, so this one
  check is performed explicitly in the router rather than purely via
  `require_permission`.

## Rate limiting

- `AuthRateLimiter` applies fixed-window counters in Redis, keyed by
  client IP and by account email, on `/auth/login`.
- Fails open if Redis is unreachable — availability of core
  authentication must not depend on a side infrastructure component
  (mirrors the project's general degraded-mode requirement for the
  LLM: a non-critical dependency being down must not take down a
  critical path).
- Disabled by default in `.env.example` (`AUTH_RATE_LIMIT_ENABLED=false`)
  for frictionless local development; must be enabled in production.

## Audit trail

- `AuditEvent` rows are append-only at the service layer (no
  update/delete service method exists for them in Foundation).
- Captures: timestamp, workspace_id (nullable — some events like a
  failed login precede workspace context), actor_user_id (nullable),
  action, resource_type/id, correlation_id, result, and a JSON
  metadata blob.
- Recorded today: bootstrap, register, login (success + failure),
  logout, workspace creation, CRM actions (`crm.organization.created`,
  `crm.organization.updated`, `crm.client.created`, `crm.client.updated`,
  `crm.client_contact.created`, `crm.client_contact.deleted`), and
  Service Desk actions (`servicedesk.queue.created/updated`,
  `servicedesk.category.created/updated`, `servicedesk.tag.created`,
  `servicedesk.ticket.created/updated/status_changed/assigned/tag_added/tag_removed`
  — status-change and assignment events carry before/after values in
  their metadata). Communication actions extend this list in Phase 5.

## Secrets and configuration

- All configuration is environment-driven (`app/core/config.py`); no
  secret or connection string is hardcoded in application code.
- `.gitignore` excludes `.env` and `.env.*` (except `*.example` files),
  matching AI-project-SRV's convention.
- `METRICS_BEARER_TOKEN` and HSTS/rate-limit production requirements
  are documented in `.env.example`; a Phase 8 production-preflight
  check (mirroring AI-project-SRV's `scripts/production-preflight.py`)
  is a recommended addition before go-live, not yet implemented here.

## Correlation and observability

- Every request gets an `X-Correlation-ID` (propagated if the caller
  supplied one, generated otherwise), available to application code
  via `get_correlation_id()` and included in every structured log line
  and every `AppError` JSON response.
- Structured JSON logs to stdout; no secret values are logged (log
  statements never include tokens, password hashes, or full request
  bodies).

## Known gaps / explicitly deferred (tracked for later phases)

- No account lockout beyond the Redis rate limiter (e.g. permanent
  lock after N failures) — deferred pending a product decision on
  self-service unlock flow.
- No user-invitation flow yet (see `docs/architecture.md` non-goals).
- No CSRF protection middleware — not yet needed since Foundation
  exposes only a JSON API consumed with `Authorization: Bearer`
  headers (not cookie-based sessions); revisit if cookie-based auth is
  ever introduced for the web client in Phase 7.
- No production-preflight startup gate (HSTS/rate-limit/JWT-secret
  strength checks) — recommended for Phase 8.
