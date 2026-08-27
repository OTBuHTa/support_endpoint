# ADR-008: Deterministic Operations layer

## Status

Accepted for Phase 6B (`v0.5.0-alpha`).

## Context

The service desk needs operator tasks, SLA tracking and notifications without turning the advisory AI layer into an execution engine. SLA state also needs to remain reconstructible when a scheduler or worker is temporarily unavailable.

## Decision

1. Support tasks are first-class workspace/ticket-scoped records with a small server-controlled lifecycle: `open` -> `done|cancelled`.
2. Task assignees must be members of the same workspace; cross-workspace task IDs are normalized to 404.
3. SLA policies are per-workspace and per ticket priority. Default targets are materialized lazily when a ticket first enters SLA evaluation, and supervisors/administrators may override them through `sla.manage`.
4. Ticket SLA clocks are based on the ticket creation timestamp, not on scheduler execution time.
5. First response is derived from the earliest customer-visible `OUTBOUND Message` belonging to the ticket. Resolution is derived from the first audited ticket transition to `resolved` or `closed`.
6. SLA state is therefore reconstructible from deterministic business history. A missed scheduler tick cannot erase the original response/resolution event.
7. SLA evaluation only sets warning/breach flags and creates in-app notifications. Anti-duplicate flags prevent repeated warning/breach notifications for the same objective.
8. Notifications are workspace-scoped and user-scoped. The API always derives the recipient from the authenticated membership; callers cannot request another user's notification stream.
9. New permissions are deny-by-default: `tasks.read`, `tasks.write`, `sla.read`, `sla.manage`, and `notifications.read`. The migration backfills these grants for existing system roles.
10. AI is not in the execution path. It cannot create/complete tasks, alter SLA policies, mark SLA objectives, or create operational notifications.

## Consequences

- Operational state is auditable and replayable from existing message/ticket history.
- Phase 6B does not require a new scheduler service to remain logically correct; a future scheduler can call the deterministic SLA evaluation service periodically.
- SLA timers currently use elapsed wall-clock minutes rather than business calendars/holidays. Business-hours calendars are a future enhancement and must not silently change historical SLA semantics.
- Notifications are in-app records only; external push/email delivery is separate adapter work.
