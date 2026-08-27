# Release v0.9.0-rc1

## Status

Release Candidate 1 for production-like deployment validation. Feature development is frozen for this candidate.

## Included milestones

- CRM and Service Desk domain with workspace isolation and deny-by-default RBAC.
- Communications with customer-visible messages, physically separate internal notes and bounded attachments.
- Knowledge base and advisory-only local LLM integration with redaction, rate limits and Redis-backed distributed circuit state.
- Deterministic tasks, SLA clocks, notifications and autonomous singleton-safe SLA scheduler.
- React/Vite Operator Control Center and ownership-scoped Customer Portal.
- Hardened production compose with private backend networking, reduced capabilities, read-only application containers and no direct API host-port exposure.
- HttpOnly/SameSite browser refresh sessions with server-side rotation and revocation.
- Structured logs, protected request metrics and PostgreSQL+Redis readiness.
- Hot-path database indexes, checksummed PostgreSQL backups and CI-tested isolated restore rehearsal.
- Per-file and per-workspace attachment storage bounds with serialized quota enforcement.

## RC1 gates

RC1 is accepted only when branch and pull-request CI both pass:

1. Python 3.12 / Ruff / pytest / whitespace.
2. Alembic upgrade and downgrade.
3. React TypeScript typecheck and Vite production build.
4. Production compose and operations/release shell validation.
5. PostgreSQL backup and isolated restore rehearsal.
6. Release metadata/invariant consistency.
7. Full hardened production compose startup plus edge smoke test.

The production smoke verifies liveness/readiness, operator UI, customer portal, disabled API docs/OpenAPI, protected metrics, runtime release version and deployed git build revision.

## Deployment boundary

This repository remains operationally independent from AI-project-SRV. It must not share PostgreSQL databases, Redis databases, Docker networks, volumes, secrets, scheduler processes or attachment storage with that project.

## Not automated by repository CI

External DNS, TLS certificate issuance, reverse-proxy/tunnel configuration, host firewall policy and off-host encrypted backup retention depend on the target environment and require deployment-host validation.

## Rollback

Before a production schema change, create and verify a fresh backup and record the current deployed git SHA. Application rollback should restore the previous source/image revision first. Database downgrade is never automatic and must only be performed when schema compatibility has been explicitly verified.
