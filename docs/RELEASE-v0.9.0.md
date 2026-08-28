# Release v0.9.0

## Status

Stable release promotion of the validated v0.9.0-rc1 line. No new product feature scope is introduced by this promotion.

## Included production baseline

- Workspace-isolated CRM and Service Desk with deny-by-default RBAC and object-level authorization guards.
- Customer communications, separate internal notes, bounded PostgreSQL-backed attachments and customer portal ownership isolation.
- Deterministic tasks, SLA clocks, notifications and singleton-safe scheduler.
- Advisory-only local LLM integration, disabled by default, with redaction, rate limits and distributed circuit state.
- Operator Control Center and Customer Portal built with React/Vite/TypeScript.
- Hardened production compose: private backend network, no direct API host-port, reduced capabilities, read-only application filesystems where applicable and protected metrics.
- HttpOnly/SameSite browser refresh sessions with server-side rotation and revocation.
- Checksummed PostgreSQL backups, isolated restore verification and mandatory pre-deploy recovery checkpoint on existing installations.
- Dedicated fail-closed public-edge verification tooling and isolated Cloudflare Tunnel service example.
- Verified off-host backup transfer tooling and daily systemd timer examples, isolated from unrelated host backup stacks.

## Promotion evidence

The RC1 line passed the complete CI matrix and repeated target-host deployments on the production runner. Existing PostgreSQL deployments produced checksummed backups, isolated restore verification succeeded, migrations completed, runtime health/readiness passed and hardened production smoke verified release/build identity.

## Stable gates

Stable v0.9.0 requires the following repository and target-host checks to remain green:

1. Python 3.12 / Ruff / pytest / whitespace.
2. Alembic upgrade and downgrade.
3. React TypeScript typecheck and Vite production build.
4. Production compose plus operations/release shell validation.
5. PostgreSQL backup and isolated restore rehearsal.
6. Stable release metadata/invariant consistency.
7. Full hardened production stack smoke.
8. Target-host deployment with a fresh backup, isolated restore verification and runtime build-identity check.

## Public-production boundary

Stable application code and public exposure are separate gates. Public production additionally requires a dedicated real HTTPS hostname, a dedicated route to `127.0.0.1:8180`, real CORS origin, successful external edge verification and an independent off-host backup destination with verified transfer.

The repository deliberately does not invent DNS names, tunnel credentials, SSH destinations or backup credentials. These environment-specific resources must be provisioned before public-production readiness is declared.

## Isolation

Support Endpoint remains operationally independent from AI-project-SRV and from unrelated host backup/tunnel stacks. Databases, Redis, Docker networks, volumes, secrets, schedulers, attachment storage, public edge configuration and off-host backup state must not be shared implicitly.

## Rollback

Each production deploy of an existing database creates a fresh checksummed backup and performs isolated restore verification before changing the application revision. The previous deployed git SHA is retained as the application rollback checkpoint. Database downgrade is never automatic.
