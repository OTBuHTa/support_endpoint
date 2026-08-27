# ADR-005: Ticket state machine, fixed enums vs. workspace-customizable lookups, assignment history

## Status
Accepted

## Context
Section H of the project charter requires a controlled ticket
lifecycle with server-enforced transitions, and section G lists
`TicketStatus`, `TicketPriority`, `Queue`, `TicketCategory`, and
`TicketAssignment` as distinct entities without specifying which
should be fixed system enums versus workspace-customizable database
rows, or how assignment history should be modeled.

## Decision

### Fixed enums: TicketStatus, TicketPriority
Both are Python `StrEnum`s (`app/models/ticket_enums.py`), not
database tables — every workspace shares exactly the same seven
statuses and four priority levels. This is deliberate: SLA logic
(Phase 6) needs to reason about status semantics uniformly (e.g. "SLA
clock pauses in WAITING_CUSTOMER") — if statuses were
workspace-customizable free text, that logic would need a
per-workspace mapping layer with no clear benefit at this project's
current scope.

### Workspace-customizable lookups: Queue, TicketCategory, Tag
These ARE real database tables, workspace-scoped, with their own
CRUD endpoints gated by `settings.manage` for writes and
`tickets.read` for reads — different businesses genuinely need
different queues ("Billing", "Technical", "Sales") and categories.

### Server-controlled state machine
`ALLOWED_TRANSITIONS` in `app/models/ticket_enums.py` is an explicit
adjacency map (not a generic "any status to any status" free-for-all).
`TicketService.transition_status` is the only way to change a ticket's
status; no endpoint accepts a raw status field on a general ticket
update. Reopening (RESOLVED/CLOSED → OPEN) is allowed; CLOSED is
otherwise terminal.

### tickets.close as a distinct permission from tickets.update
Per section E's example permission list, `tickets.close` exists
separately from `tickets.update`. We enforce this specifically at the
transition endpoint: moving *to* `CLOSED` requires `tickets.close` in
addition to the `tickets.update` the endpoint already requires for
every other transition. Operator has `tickets.update` but not
`tickets.close` (Supervisor/Administrator have both) — see the
regression test `test_operator_can_update_but_not_close_ticket`.

### TicketAssignment as an append-only history log, not a single row
`Ticket.assignee_user_id` is a denormalized pointer to the *current*
assignee (fast filtering: "show me tickets assigned to X"). Every
assignment *change* — including unassignment (`assignee_user_id=null`)
— additionally appends a row to `TicketAssignment`, which is never
updated or deleted. This satisfies the "maintain ticket history"
requirement (section H) specifically for the assignment dimension,
queryable via `GET /tickets/{id}/assignments`.

### Assignee must be a workspace member
`TicketService._validate_assignee` checks `WorkspaceMembership`
before allowing an assignment — assigning a ticket to a user with no
membership in the workspace is rejected (422), preventing tickets from
being silently "orphaned" to an inaccessible assignee.

## Rejected alternatives
- **A single `assigned_to` column with no history table** was
  rejected: it would make "who was this ticket assigned to last
  Tuesday" unanswerable, which service-desk reporting typically needs.
- **Making TicketStatus/TicketPriority workspace-customizable tables**
  (matching the `Queue`/`TicketCategory` pattern) was rejected for now
  — see "Fixed enums" above. Revisit if a genuine business need for
  custom priority levels emerges.
- **A generic field-level ticket history/audit table** (recording
  every field change, not just status/assignment) was considered and
  deferred: the generic `AuditEvent` log already records
  `servicedesk.ticket.updated`/`status_changed`/`assigned` events with
  enough context for Foundation's needs; a full per-field version
  history is a larger feature that can be added later without
  changing the `Ticket` schema itself.

## Consequences
- Adding a new status or changing transition rules is a one-line
  change to `ALLOWED_TRANSITIONS`, not a data migration.
- Reporting on "time in each status" (a natural SLA building block for
  Phase 6) can be derived from `AuditEvent` rows with
  `action=servicedesk.ticket.status_changed`, since each carries
  `metadata={"from": ..., "to": ...}` and a timestamp.
