# ADR-006: Communications, internal visibility, and attachments

## Status

Accepted for Phase 5 (`v0.3.0-alpha`).

## Context

A Service Desk ticket needs threaded customer communication while preserving a hard boundary between customer-visible messages and operator-only context. Phase 5 also needs channel-neutral storage and attachments without introducing external email/chat delivery integrations yet.

## Decision

1. `Conversation` is workspace- and ticket-scoped and carries a `channel` abstraction (`web`, `email`, `chat`, `phone`, `api`) plus optional external thread reference.
2. `Message` contains only customer-visible communication and has an explicit direction (`inbound` or `outbound`). There is deliberately no `is_internal` flag.
3. `InternalNote` is a separate table and separate API surface. It is protected by `tickets.internal_comment`; normal message-list endpoints can never return internal notes because they query a different entity.
4. Every conversation/message/note lookup is resolved through the `(workspace_id, ticket_id, object_id)` boundary. Cross-workspace IDs return 404.
5. Attachments belong to exactly one `Message` or `InternalNote`. Phase 5 stores attachment bytes in this project's own PostgreSQL database, capped at 5 MiB per object, with SHA-256 recorded for integrity. Internal-note attachments inherit the internal-note authorization boundary.
6. Phase 5 records inbound/outbound messages but does **not** send email/chat messages or poll external providers. External adapters are later work and must call deterministic service-layer methods rather than bypass authorization/audit.

## Consequences

- Internal content cannot leak through a forgotten `WHERE is_internal = false` filter because it is not stored in the customer-message table.
- The database blob approach keeps Phase 5 self-contained and testable but is not intended for large-file production workloads. Phase 8 may move content to object storage behind the same attachment IDs and authorization checks.
- Channel adapters remain decoupled from the core domain model.
- `AI-project-SRV` remains operationally independent; no database, volume, secret, network, or API mutation is shared.
