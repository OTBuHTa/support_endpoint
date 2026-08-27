# ADR-009: Operator Control Center and client portal boundary

## Status

Accepted for Phase 7A (`v0.6.0-alpha`).

## Context

The backend contracts are mature enough for a production-style operator surface, while customer portal authorization is not: workspace `User` identities and CRM `Client` records are currently separate domains with no authoritative binding.

## Decision

1. Replace the nginx placeholder with a React 18 + Vite + TypeScript operator application.
2. Keep same-origin `/api` calls through nginx; the browser never calls Postgres, Redis or the LLM directly.
3. Store access/refresh tokens in `sessionStorage` for the current alpha and rotate through the existing `/auth/refresh` contract. Phase 8 will review browser token storage against the final deployment threat model.
4. Load workspace permission codes from `/workspaces/{workspace_id}/my-permissions` and use them only for presentation gating. Backend `require_permission` and object-level checks remain authoritative.
5. Ship read-oriented operational vertical slices first: Overview, Tickets, Clients, Tasks, Knowledge and Notifications. Mutation workflows are added incrementally against existing endpoints rather than inventing frontend-only capabilities.
6. Do not present a fake customer portal by reusing operator APIs or role names.
7. Phase 7B must first introduce an explicit, auditable `User ↔ Client` binding and ownership-scoped portal endpoints with IDOR regressions. Only then may the frontend expose customer ticket/message data.
8. Frontend typecheck and production build are mandatory CI gates alongside the existing API and Alembic jobs.

## Consequences

- Operators gain a real responsive control center without weakening backend authorization.
- UI availability reflects permissions but cannot grant them.
- The client portal remains blocked until its identity boundary exists, avoiding a cross-customer data-exposure class of bugs.
- The web image becomes a deterministic multi-stage Node build served by nginx rather than static placeholder assets.
