# ADR-011: Production observability and recovery boundary

Status: Accepted  
Date: 2026-08-27

## Context

Phase 8B needs useful production signals and a recovery procedure without weakening tenant isolation, exposing customer data through metrics, or introducing a new external observability SaaS dependency.

## Decision

1. The API exposes a small Prometheus-text endpoint at `/api/v1/metrics` protected by a dedicated bearer token. When no token is configured the endpoint behaves as not found.
2. Metric labels are deliberately low-cardinality and contain no workspace IDs, user IDs, ticket IDs, URLs with query strings, email addresses or other customer data. Request metrics are grouped only by HTTP method and status class.
3. JSON request-completion logs may contain correlation ID, method, path, status code and duration. Request bodies, authorization headers, cookies and token values are never included by the request middleware.
4. Readiness covers PostgreSQL and Redis because both are required for the production application path. The optional advisory LLM is excluded from readiness so an AI outage cannot take the Service Desk offline.
5. Hot-path database indexes are introduced by an Alembic migration with a tested downgrade. They target actual repository access patterns rather than speculative full-text or broad index creation.
6. PostgreSQL custom-format backups are checksummed. A backup is not considered operationally verified until it restores successfully into a separate temporary database and a schema marker can be read.
7. Attachments remain database-backed in this milestone, so PostgreSQL backup includes their binary content. Moving attachments to object storage requires a separate decision that preserves the same authorization boundary and adds independent object backup/restore.
8. Backup retention and off-host replication are deployment policy, not silently embedded into the application. The runbook requires off-host storage but does not assume a paid provider.

## Consequences

- Metrics are intentionally smaller than a full OpenTelemetry/Prometheus instrumentation suite, but are safe to expose through a controlled local scrape path.
- In-process counters reset when an API worker restarts and are per-process if multiple workers are introduced. A multi-worker metrics aggregation design can be added later if deployment topology requires it.
- Composite indexes increase write/storage cost slightly in exchange for predictable ticket, task, SLA, audit and notification reads.
- CI performs a real PostgreSQL backup/restore rehearsal, making recovery scripts executable contracts rather than documentation-only procedures.
- Browser-session hardening and scheduler reliability remain separate production-hardening decisions so they can be reviewed without coupling them to observability or schema-index changes.
