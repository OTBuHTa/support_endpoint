# Domain model (Foundation phase)

Only the identity/tenancy/RBAC substrate exists so far. CRM and
Service Desk entities (Client, Ticket, Queue, SLAPolicy, etc.) arrive
in Phases 3–6 per `docs/architecture.md`.

## Entities

### User
Global identity, not tenant-scoped. `email` (unique), `password_hash`,
`full_name`, `is_active`. A user may belong to zero or more workspaces
via `WorkspaceMembership`.

### Workspace
The tenant boundary. `name`, `slug` (unique, URL-safe, auto-derived
from `name` with a numeric suffix on collision).

### WorkspaceMembership
The join table between `User` and `Workspace`, carrying exactly one
`Role`. Unique on `(workspace_id, user_id)` — a user has at most one
role per workspace in Foundation (multiple simultaneous roles per
workspace is an explicit non-goal for now; revisit if a real use case
emerges).

### Role
A named, reusable bundle of permissions. Four system roles seeded on
first use (idempotently, via `ensure_system_roles`): `client`,
`operator`, `supervisor`, `administrator`. `is_system=True` marks
these as not user-deletable (enforcement of that constraint is a
Phase 3+ item once a role-management endpoint exists).

### Permission
An atomic capability string, e.g. `tickets.create`. See
`app/authz/permissions.py` for the canonical list and
`SYSTEM_ROLE_PERMISSIONS` for which system role gets which codes.

### RolePermission
Join table between `Role` and `Permission`. Unique on
`(role_id, permission_id)`.

### RefreshSession
One row per issued refresh token (opaque, hashed). See ADR-002 for the
rotation/revocation model.

### AuditEvent
Append-only security/business-action log. See `docs/security.md`.

### ClientOrganization
A company/business account (B2B), optional. `name`, `domain`, `notes`,
`is_active`. See ADR-004 for the full rationale behind this split.

### Client
The primary CRM record — one individual person/account-holder that a
future Ticket (Phase 4) attaches to. `full_name`, `primary_email`,
`primary_phone`, `notes`, `is_active`, optional `organization_id`
(validated to belong to the same workspace).

### ClientContact
Zero or more additional labeled contact channels for a `Client`
(`label`, `channel_type` — email/phone/other, `value`). Hard-deleted
(no soft-delete) since it carries no history of its own.

### TicketStatus / TicketPriority
Fixed, system-wide `StrEnum`s, not database tables — see ADR-005.
Status: `new`, `open`, `in_progress`, `waiting_customer`,
`waiting_internal`, `resolved`, `closed`. Priority: `low`, `medium`,
`high`, `urgent`.

### Queue / TicketCategory / Tag
Workspace-customizable lookup tables (`name`, `description`/`color`,
`is_active` where applicable). Writes require `settings.manage`; reads
require `tickets.read`.

### Ticket
The core Service Desk record. `subject`, `description`, `status`,
`priority`, required `client_id`, required `creator_user_id`, optional
`assignee_user_id`/`queue_id`/`category_id` (all validated to belong
to the same workspace). Status changes only through the server-side
state machine (ADR-005) — no endpoint lets a caller set `status`
directly on a general update.

### TicketAssignment
Append-only history of assignment changes for a ticket (including
unassignment). See ADR-005.

### TicketTag
Many-to-many join between `Ticket` and `Tag`.

## Entity relationship summary

```
User ──< WorkspaceMembership >── Workspace
              │
              ▼
             Role ──< RolePermission >── Permission

User ──< RefreshSession

Workspace ──< AuditEvent >── User (actor, nullable)

Workspace ──< ClientOrganization
Workspace ──< Client >── ClientOrganization (optional, same workspace)
Client ──< ClientContact

Workspace ──< Queue
Workspace ──< TicketCategory
Workspace ──< Tag

Workspace ──< Ticket >── Client (required)
Ticket >── User (creator, required; assignee, optional)
Ticket >── Queue (optional)
Ticket >── TicketCategory (optional)
Ticket ──< TicketAssignment (history)
Ticket ──< TicketTag >── Tag
```

## What is deliberately NOT modeled yet

Per `docs/architecture.md`'s phase plan: Conversation, Message,
InternalNote, Attachment (Phase 5), Task, SLAPolicy, SLAEvent,
KnowledgeArticle, Notification (Phase 6). These arrive without needing
to change the identity/tenancy/RBAC/CRM/Service-Desk substrate defined
here. A user-invitation endpoint (inviting an existing user into
someone else's workspace) is also not yet implemented — see
`docs/architecture.md` Foundation non-goals.
